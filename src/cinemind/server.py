import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from src.cinemind.config import settings, PROJECT_ROOT
from src.cinemind.data.build_catalog import load_catalog, CatalogMissing
from src.cinemind.llm import LLMClient, default_llm
from src.cinemind.pipeline import Pipeline
from src.cinemind.retrieval.graph import MovieGraph
from src.cinemind.schemas import HealthResponse, RecommendRequest, Trace
from src.cinemind.trace import TraceManager

app = FastAPI(title="CineMind API", version="1.0.0")

# Enable CORS for localhost access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

trace_manager = TraceManager()
_pipeline: Optional[Pipeline] = None


def get_pipeline() -> Pipeline:
    """Built on first live request so replay works before `make index`."""
    global _pipeline
    if _pipeline is None:
        _pipeline = Pipeline()
    return _pipeline

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    model_ready = await default_llm.ping()
    try:
        catalog_size = len(load_catalog())
    except CatalogMissing:
        catalog_size = 0
    graph_ready = settings.graph_path.exists()
    return HealthResponse(
        model_ready=model_ready,
        catalog_size=catalog_size,
        graph_ready=graph_ready,
        model_name=settings.llm_model
    )

def _load_scenarios() -> list:
    sc_file = settings.scenarios_path
    if not sc_file.exists():
        return []
    with open(sc_file, "r", encoding="utf-8") as f:
        return json.load(f)


_stats_cache: Dict[str, Any] = {}


@app.get("/api/stats")
async def get_stats():
    """Catalog and graph sizes measured from the built data (no hardcoded numbers)."""
    key = f"{settings.catalog_path.stat().st_mtime if settings.catalog_path.exists() else 0}"
    if _stats_cache.get("key") != key:
        stats: Dict[str, Any] = {"catalog_size": 0, "cold_start": 0, "graph_nodes": 0, "graph_edges": 0,
                                 "cutoff_ts": None}
        try:
            movies = load_catalog()
            stats["catalog_size"] = len(movies)
            stats["cold_start"] = sum(1 for m in movies if m.n_ratings_train == 0)
        except CatalogMissing:
            pass
        if settings.graph_path.exists():
            g = MovieGraph.load().g
            stats["graph_nodes"], stats["graph_edges"] = g.number_of_nodes(), g.number_of_edges()
        meta = settings.catalog_path.parent / "split_meta.json"
        if meta.exists():
            stats["cutoff_ts"] = json.loads(meta.read_text(encoding="utf-8")).get("cutoff_ts")
        _stats_cache.update(key=key, stats=stats)
    return _stats_cache["stats"]


@app.get("/api/scenarios")
async def get_scenarios():
    return _load_scenarios()

@app.get("/api/compare/{scenario_id}")
async def get_compare_scenario(scenario_id: str):
    v_trace = trace_manager.get_scenario_trace(scenario_id, config="vector")
    h_trace = trace_manager.get_scenario_trace(scenario_id, config="hybrid")

    if not v_trace and not h_trace:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' replay traces not found")

    return {
        "scenario_id": scenario_id,
        "vector": v_trace.model_dump() if v_trace else None,
        "hybrid": h_trace.model_dump() if h_trace else None
    }

@app.get("/api/results")
async def get_results():
    res_path = settings.results_path
    if not res_path.exists():
        return {"error": "Evaluation results not yet generated. Run `make eval` first."}
    with open(res_path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.post("/api/recommend")
async def recommend_stream(request: RecommendRequest):
    # 1. Validation: Reject empty query AND empty history with 400
    has_query = bool(request.query and request.query.strip())
    has_history = bool(request.history and len(request.history) > 0)

    if not has_query and not has_history and not (request.replay and request.scenario_id):
        raise HTTPException(
            status_code=400,
            detail="Empty request: Both query and viewing history are empty. Please provide a search query or select a history profile."
        )

    # 2. Replay mode (if replay requested)
    if request.replay:
        target_id = request.scenario_id
        if not target_id:
            raise HTTPException(
                status_code=400,
                detail="Saved runs exist only for the examples. Pick an example, or switch to Live AI."
            )
        if target_id:
            trace = (trace_manager.get_scenario_trace(target_id, config=request.retrieval)
                     or trace_manager.get_scenario_trace(target_id, config="hybrid"))
            if not trace:
                raise HTTPException(
                    status_code=404,
                    detail=f"No recorded replay for scenario '{target_id}'."
                )
            if trace:
                async def replay_generator():
                    for st in trace.stages:
                        yield {
                            "event": "stage_start",
                            "data": json.dumps({"stage": st.name, "started": st.started, "replay": True})
                        }
                        await asyncio.sleep(0.04)
                        yield {
                            "event": "stage_end",
                            "data": json.dumps({"stage": st.name, "record": st.model_dump(), "replay": True})
                        }
                        await asyncio.sleep(0.04)

                    yield {
                        "event": "final",
                        "data": json.dumps(trace.model_dump())
                    }

                return EventSourceResponse(replay_generator())

    # 3. Live mode: Check model server availability
    if request.scenario_id and not any(sc.get("id") == request.scenario_id for sc in _load_scenarios()):
        raise HTTPException(status_code=404, detail=f"Unknown scenario '{request.scenario_id}'.")
    if request.mode == "feed" and request.scenario_id and not has_history:
        sc = next(sc for sc in _load_scenarios() if sc["id"] == request.scenario_id)
        request = request.model_copy(update={"history": sc.get("history") or []})

    model_online = await default_llm.ping()
    if not model_online and not default_llm.stub:
        raise HTTPException(
            status_code=503,
            detail="The local model server (Ollama) is unavailable. Please check that Ollama is running or switch to Replay mode."
        )

    # 4. Stream live stages via SSE
    async def event_generator():
        queue: asyncio.Queue = asyncio.Queue()

        async def sse_callback(ev_type: str, data: Dict[str, Any]):
            await queue.put({"event": ev_type, "data": json.dumps(data)})

        async def worker():
            try:
                await get_pipeline().run(request, emit_callback=sse_callback)
            except Exception as e:
                import traceback
                print(f"[Server Error] Pipeline processing failed: {e}", flush=True)
                traceback.print_exc()
                await queue.put({
                    "event": "error",
                    "data": json.dumps({"error": str(e), "message": f"Pipeline processing failed: {str(e)}"})
                })
            finally:
                await queue.put(None)  # Sentinel

        task = asyncio.create_task(worker())

        while True:
            msg = await queue.get()
            if msg is None:
                break
            yield msg

        await task

    return EventSourceResponse(event_generator())

# Static files mount
static_dir = PROJECT_ROOT / "src" / "cinemind" / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/")
async def serve_index():
    index_file = static_dir / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>CineMind API is running. Build UI in static/index.html</h1>")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.cinemind.server:app", host=settings.server_host, port=settings.server_port, reload=False)
