import pytest
from pathlib import Path
from src.cinemind.llm import LLMClient
from src.cinemind.pipeline import Pipeline
from src.cinemind.schemas import RecommendRequest, Rated, Trace
from src.cinemind.trace import TraceManager

@pytest.mark.asyncio
async def test_pipeline_stub_execution(tmp_path: Path):
    llm = LLMClient(stub=True, stub_mode="valid")
    pipeline = Pipeline(llm=llm)

    events = []
    async def capture_event(ev_type, data):
        events.append((ev_type, data))

    req = RecommendRequest(
        mode="query",
        query="Mind-bending science fiction like Inception",
        history=[Rated(movie_id=79132, title="Inception", rating=5.0)],
        retrieval="hybrid"
    )

    trace = await pipeline.run(req, emit_callback=capture_event)

    # 1. Trace contains 4 agent stages plus retrieval (5 stages total)
    stage_names = [s.name for s in trace.stages]
    assert stage_names == ["understanding", "retrieval", "judging", "summarising", "ranking"]

    # 2. Returned ids subset of candidates and disjoint with history
    cand_ids = {c.movie_id for c in trace.candidates}
    final_ids = [f.movie_id for f in trace.final]

    assert len(final_ids) == 5
    for fid in final_ids:
        assert fid in cand_ids
        assert fid != 79132  # Inception was in history!

    # Check SSE events emitted
    event_names = [e[0] for e in events]
    assert "stage_start" in event_names
    assert "stage_end" in event_names
    assert "final" in event_names

    # 3. Trace round-trips without loss
    tm = TraceManager(traces_dir=tmp_path / "traces")
    saved_path = tm.save_trace(trace)
    loaded_trace = tm.load_trace(saved_path)

    assert loaded_trace.run_id == trace.run_id
    assert len(loaded_trace.final) == len(trace.final)
    assert loaded_trace.metrics == trace.metrics
