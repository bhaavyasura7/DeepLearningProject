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
from src.cinemind.data.build_catalog import load_catalog
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
pipeline = Pipeline()

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    model_ready = await default_llm.ping()
    catalog = load_catalog()
    graph_ready = settings.graph_path.exists()
    return HealthResponse(
        model_ready=model_ready,
        catalog_size=len(catalog),
        graph_ready=graph_ready,
        model_name=settings.llm_model
    )

@app.get("/api/scenarios")
async def get_scenarios():
    sc_file = settings.scenarios_path
    if not sc_file.exists():
        return []
    with open(sc_file, "r", encoding="utf-8") as f:
        return json.load(f)

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

    if not has_query and not has_history:
        raise HTTPException(
            status_code=400,
            detail="Empty request: Both query and viewing history are empty. Please provide a search query or select a history profile."
        )

    # 2. Replay mode
    if request.replay:
        if not request.scenario_id:
            raise HTTPException(status_code=400, detail="Replay mode requires a valid 'scenario_id'.")
        trace = trace_manager.get_scenario_trace(request.scenario_id, config=request.retrieval)
        if not trace:
            raise HTTPException(status_code=404, detail=f"Recorded replay trace for scenario '{request.scenario_id}' with config '{request.retrieval}' not found.")

        async def replay_generator():
            for st in trace.stages:
                yield {
                    "event": "stage_start",
                    "data": json.dumps({"stage": st.name, "started": st.started, "replay": True})
                }
                await asyncio.sleep(0.05)
                yield {
                    "event": "stage_end",
                    "data": json.dumps({"stage": st.name, "record": st.model_dump(), "replay": True})
                }
                await asyncio.sleep(0.05)

            yield {
                "event": "final",
                "data": json.dumps(trace.model_dump())
            }

        return EventSourceResponse(replay_generator())

    # 3. Live mode: Check model server availability
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
                await pipeline.run(request, emit_callback=sse_callback)
            except Exception as e:
                await queue.put({
                    "event": "error",
                    "data": json.dumps({"error": str(e), "message": "Pipeline processing failed."})
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
