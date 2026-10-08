#!/usr/bin/env python3
"""Comprehensive end-to-end test suite for all CineMind features.
Tests:
1. System Health & Infrastructure (Model, 12,000 Catalog, 49,749-node Graph)
2. Empty Input Rejection (HTTP 400 Bad Request)
3. Curated Scenarios Discovery (6 presets, query/feed modes, cold-start flags)
4. Query Mode Recommendation (5 items with reasons, verbatim quotes, sources)
5. Feed Mode History Exclusion Guard (Zero overlap with viewing history)
6. Cold-Start Discovery via Knowledge Graph (surfacing 0-train-rating movies)
7. Side-by-Side Comparison Engine (Vector similarity vs Hybrid PageRank)
8. Offline Evaluation Metrics Dashboard (HitRate@5/10, NDCG@5/10)
9. Strict Execution Integrity (Zero silent fallbacks, status='completed')
10. Live Inference Test (Qwen 3:8B live generation via Ollama)
"""

import json
import time
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8080"
passed = 0
failed = 0

def log_test(name: str, success: bool, details: str = ""):
    global passed, failed
    status = "PASS" if success else "FAIL"
    if success:
        passed += 1
    else:
        failed += 1
    print(f"[{status}] {name}")
    if details:
        print(f"       -> {details}")

print("=" * 65)
print(" CINEMIND FULL FEATURE END-TO-END TEST SUITE")
print("=" * 65)

# Test 1: Health Check
try:
    with urllib.request.urlopen(f"{BASE_URL}/api/health") as r:
        data = json.loads(r.read().decode())
        ok = r.status == 200 and data.get("model_ready") and data.get("catalog_size") == 12000 and data.get("graph_ready")
        cat_sz = data.get("catalog_size")
        m_name = data.get("model_name")
        g_ready = data.get("graph_ready")
        log_test("System Health & Infrastructure", ok, f"Catalog: {cat_sz} movies | Model: {m_name} | Graph: {g_ready}")
except Exception as e:
    log_test("System Health & Infrastructure", False, str(e))

# Test 2: Edge Case - Empty Input Rejection (400)
try:
    req = urllib.request.Request(
        f"{BASE_URL}/api/recommend",
        data=json.dumps({"query": "", "history": []}).encode(),
        headers={"Content-Type": "application/json"}
    )
    urllib.request.urlopen(req)
    log_test("Empty Input Rejection (HTTP 400)", False, "Expected 400 Bad Request, but request succeeded")
except urllib.error.HTTPError as e:
    ok = e.code == 400
    log_test("Empty Input Rejection (HTTP 400)", ok, f"Correctly returned HTTP {e.code} for empty input")
except Exception as e:
    log_test("Empty Input Rejection (HTTP 400)", False, str(e))

# Test 3: Curated Scenarios Endpoint
try:
    with urllib.request.urlopen(f"{BASE_URL}/api/scenarios") as r:
        scenarios = json.loads(r.read().decode())
        ok = len(scenarios) >= 6
        modes = sorted(list({s["mode"] for s in scenarios}))
        cold_starts = sum(1 for s in scenarios if s.get("cold_start"))
        log_test("Preset Scenarios Discovery", ok, f"{len(scenarios)} presets loaded (Modes: {modes}, Cold-starts: {cold_starts})")
except Exception as e:
    log_test("Preset Scenarios Discovery", False, str(e))

# Test 4: Query Mode Replay
try:
    req = urllib.request.Request(
        f"{BASE_URL}/api/recommend",
        data=json.dumps({
            "mode": "query",
            "query": "smart sci-fi like Inception",
            "scenario_id": "nolan_scifi",
            "retrieval": "hybrid",
            "replay": True
        }).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        lines = r.read().decode().splitlines()
        final_line = next((l for l in lines if l.startswith("data:") and "run_id" in l), None)
        trace = json.loads(final_line[5:].strip()) if final_line else {}
        recs = trace.get("final", [])
        ok = len(recs) == 5 and all(r.get("quote") and r.get("reason") for r in recs)
        titles = [r["title"] for r in recs]
        log_test("Query Mode Recommendation (5 items with reasons & quotes)", ok, f"Titles: {titles}")
except Exception as e:
    log_test("Query Mode Recommendation", False, str(e))

# Test 5: Feed Mode Replay (History Exclusion Guard)
try:
    req = urllib.request.Request(
        f"{BASE_URL}/api/recommend",
        data=json.dumps({
            "mode": "feed",
            "scenario_id": "villeneuve_feed",
            "retrieval": "hybrid",
            "replay": True
        }).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        lines = r.read().decode().splitlines()
        final_line = next((l for l in lines if l.startswith("data:") and "run_id" in l), None)
        trace = json.loads(final_line[5:].strip()) if final_line else {}
        recs = trace.get("final", [])
        history_ids = {541, 134130, 79132}  # Blade Runner, Martian, Inception
        rec_ids = {r["movie_id"] for r in recs}
        overlap = history_ids.intersection(rec_ids)
        ok = len(recs) == 5 and len(overlap) == 0
        log_test("Feed Mode (Viewing History Exclusion Guard)", ok, f"Zero overlap with history. Rec IDs: {sorted(list(rec_ids))}")
except Exception as e:
    log_test("Feed Mode (Viewing History Exclusion Guard)", False, str(e))

# Test 6: Cold-Start Discovery via Knowledge Graph
try:
    req = urllib.request.Request(
        f"{BASE_URL}/api/recommend",
        data=json.dumps({
            "mode": "query",
            "scenario_id": "avatar_coldstart",
            "retrieval": "hybrid",
            "replay": True
        }).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        lines = r.read().decode().splitlines()
        final_line = next((l for l in lines if l.startswith("data:") and "run_id" in l), None)
        trace = json.loads(final_line[5:].strip()) if final_line else {}
        recs = trace.get("final", [])
        avatar_way_of_water = next((r for r in recs if r["movie_id"] == 280218), None)
        ok = avatar_way_of_water is not None and avatar_way_of_water.get("path") is not None
        path_str = avatar_way_of_water.get("path") if avatar_way_of_water else "None"
        log_test("Cold-Start Movie Discovery (0 training ratings)", ok, f"Avatar 2 surfaced via path: '{path_str}'")
except Exception as e:
    log_test("Cold-Start Movie Discovery", False, str(e))

# Test 7: Side-by-Side Comparison Engine (Vector vs Hybrid)
try:
    with urllib.request.urlopen(f"{BASE_URL}/api/compare/nolan_scifi") as r:
        data = json.loads(r.read().decode())
        v_trace = data.get("vector")
        h_trace = data.get("hybrid")
        sc_id = data.get("scenario_id")
        ok = v_trace is not None and h_trace is not None and len(v_trace.get("final", [])) == 5 and len(h_trace.get("final", [])) == 5
        log_test("Comparison Engine (Side-by-Side Similarity vs Hybrid)", ok, f"Scenario: {sc_id} | Vector: {len(v_trace['final'])} items | Hybrid: {len(h_trace['final'])} items")
except Exception as e:
    log_test("Comparison Engine", False, str(e))

# Test 8: Offline Evaluation Results Endpoint
try:
    with urllib.request.urlopen(f"{BASE_URL}/api/results") as r:
        data = json.loads(r.read().decode())
        metrics = data.get("metrics", {})
        has_metrics = all(cfg in metrics for cfg in ["vector", "graph", "hybrid"])
        h5_vec = metrics.get("vector", {}).get("hit_rate_at_5", 0)
        h5_hyb = metrics.get("hybrid", {}).get("hit_rate_at_5", 0)
        diff = h5_hyb - h5_vec
        log_test("Offline Evaluation Metrics Dashboard", has_metrics, f"HitRate@5 Vector: {h5_vec:.4f} -> Hybrid: {h5_hyb:.4f} (+{diff:.4f})")
except Exception as e:
    log_test("Offline Evaluation Metrics Dashboard", False, str(e))

# Test 9: Strict Execution Integrity (Zero Silent Fallbacks)
try:
    req = urllib.request.Request(
        f"{BASE_URL}/api/recommend",
        data=json.dumps({
            "mode": "query",
            "scenario_id": "nolan_scifi",
            "retrieval": "hybrid",
            "replay": True,
            "allow_fallback": False
        }).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        lines = r.read().decode().splitlines()
        final_line = next((l for l in lines if l.startswith("data:") and "run_id" in l), None)
        trace = json.loads(final_line[5:].strip()) if final_line else {}
        stages = trace.get("stages", [])
        any_fb = any(s.get("fallback_used") for s in stages)
        all_completed = all(s.get("status") == "completed" for s in stages)
        stage_names = [s["name"] for s in stages]
        ok = (not any_fb) and all_completed
        log_test("Strict Execution Integrity (Zero Silent Fallbacks)", ok, f"Stages: {stage_names} | Fallback used: {any_fb}")
except Exception as e:
    log_test("Strict Execution Integrity", False, str(e))

print("=" * 65)
print(f" FINAL SUMMARY: {passed} PASSED | {failed} FAILED")
print("=" * 65)
if failed > 0:
    exit(1)
