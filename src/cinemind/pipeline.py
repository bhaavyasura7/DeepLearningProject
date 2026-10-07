import asyncio
import time
import uuid
from typing import Optional, Callable, Dict, Any, List, Set
from src.cinemind.agents.judge import JudgingAgent
from src.cinemind.agents.rank import RankingAgent
from src.cinemind.agents.summarise import SummarisingAgent
from src.cinemind.agents.understand import UnderstandingAgent, EmptyInput
from src.cinemind.config import settings
from src.cinemind.llm import LLMClient, default_llm
from src.cinemind.retrieval.hybrid import HybridRetriever
from src.cinemind.schemas import RecommendRequest, Trace, StageRecord, Profile, Candidate, Verdict, Brief, RankedItem

class Pipeline:
    def __init__(
        self,
        llm: Optional[LLMClient] = None,
        retriever: Optional[HybridRetriever] = None
    ):
        self.llm = llm or default_llm
        self.retriever = retriever or HybridRetriever()
        self.understand_agent = UnderstandingAgent(llm=self.llm)
        self.judge_agent = JudgingAgent(llm=self.llm)
        self.summarise_agent = SummarisingAgent(llm=self.llm)
        self.rank_agent = RankingAgent(llm=self.llm)

    async def run(
        self,
        request: RecommendRequest,
        emit_callback: Optional[Callable[[str, Dict[str, Any]], Any]] = None
    ) -> Trace:
        run_id = f"run_{uuid.uuid4().hex[:10]}"
        t_start = time.time()
        initial_calls = self.llm.call_count

        stages: List[StageRecord] = []

        async def emit(event_type: str, data: Dict[str, Any]):
            if emit_callback:
                if asyncio.iscoroutinefunction(emit_callback):
                    await emit_callback(event_type, data)
                else:
                    emit_callback(event_type, data)

        # Extract history IDs and seed IDs
        history_ids: Set[int] = set()
        seed_ids: List[int] = []
        if request.history:
            for item in request.history:
                history_ids.add(item.movie_id)
                if item.rating >= 4.0:
                    seed_ids.append(item.movie_id)

        # --- Stage 1: Understanding ---
        s1_start = time.time()
        await emit("stage_start", {"stage": "understanding", "started": s1_start})
        try:
            profile = await self.understand_agent.understand(history=request.history, query=request.query)
            s1_end = time.time()
            s1_rec = StageRecord(
                name="understanding",
                started=s1_start,
                ended=s1_end,
                status="completed",
                fallback_used=False,
                output=profile.model_dump()
            )
            stages.append(s1_rec)
            await emit("stage_end", {"stage": "understanding", "record": s1_rec.model_dump()})
        except Exception as e:
            s1_end = time.time()
            s1_rec = StageRecord(
                name="understanding",
                started=s1_start,
                ended=s1_end,
                status="failed",
                error=str(e)
            )
            stages.append(s1_rec)
            await emit("stage_end", {"stage": "understanding", "record": s1_rec.model_dump()})
            raise

        # --- Stage 2: Retrieval ---
        s2_start = time.time()
        await emit("stage_start", {"stage": "retrieval", "started": s2_start})
        candidates = self.retriever.retrieve(
            profile_text=profile.summary,
            query=request.query,
            seed_ids=seed_ids,
            history_ids=history_ids,
            config=request.retrieval
        )
        s2_end = time.time()
        s2_rec = StageRecord(
            name="retrieval",
            started=s2_start,
            ended=s2_end,
            status="completed",
            fallback_used=False,
            output={"candidate_count": len(candidates), "candidates": [c.model_dump() for c in candidates]}
        )
        stages.append(s2_rec)
        await emit("stage_end", {"stage": "retrieval", "record": s2_rec.model_dump()})

        # --- Stage 3: Judging ---
        s3_start = time.time()
        await emit("stage_start", {"stage": "judging", "started": s3_start})
        verdicts, judge_fb = await self.judge_agent.judge(profile, candidates)
        s3_end = time.time()
        s3_rec = StageRecord(
            name="judging",
            started=s3_start,
            ended=s3_end,
            status="fallback" if judge_fb else "completed",
            fallback_used=judge_fb,
            output={"verdicts": [v.model_dump() for v in verdicts]}
        )
        stages.append(s3_rec)
        await emit("stage_end", {"stage": "judging", "record": s3_rec.model_dump()})

        # --- Stage 4: Summarising ---
        s4_start = time.time()
        await emit("stage_start", {"stage": "summarising", "started": s4_start})
        brief, sum_fb = await self.summarise_agent.summarise(profile, verdicts, candidates)
        s4_end = time.time()
        s4_rec = StageRecord(
            name="summarising",
            started=s4_start,
            ended=s4_end,
            status="fallback" if sum_fb else "completed",
            fallback_used=sum_fb,
            output=brief.model_dump()
        )
        stages.append(s4_rec)
        await emit("stage_end", {"stage": "summarising", "record": s4_rec.model_dump()})

        # --- Stage 5: Ranking ---
        s5_start = time.time()
        await emit("stage_start", {"stage": "ranking", "started": s5_start})
        ranked_items, rank_fb = await self.rank_agent.rank(
            profile=profile,
            brief=brief,
            candidates=candidates,
            verdicts=verdicts,
            k=settings.final_k,
            history_ids=history_ids
        )
        s5_end = time.time()
        s5_rec = StageRecord(
            name="ranking",
            started=s5_start,
            ended=s5_end,
            status="fallback" if rank_fb else "completed",
            fallback_used=rank_fb,
            output={"rankings": [r.model_dump() for r in ranked_items]}
        )
        stages.append(s5_rec)
        await emit("stage_end", {"stage": "ranking", "record": s5_rec.model_dump()})

        total_duration = time.time() - t_start
        llm_calls_made = self.llm.call_count - initial_calls

        trace = Trace(
            run_id=run_id,
            mode=request.mode,
            input=request.model_dump(),
            config=request.retrieval,
            stages=stages,
            candidates=candidates,
            final=ranked_items,
            metrics={
                "llm_calls": llm_calls_made,
                "seconds": round(total_duration, 2)
            }
        )

        await emit("final", trace.model_dump())
        return trace
