import json
import time
import urllib.request

print("Testing Live SSE recommendation stream with Qwen 3:8B...")
t0 = time.time()
req = urllib.request.Request(
    "http://127.0.0.1:8080/api/recommend",
    data=json.dumps({
        "mode": "query",
        "query": "cerebral sci-fi thriller like inception",
        "retrieval": "vector",
        "replay": False,
        "allow_fallback": False
    }).encode(),
    headers={"Content-Type": "application/json"}
)

with urllib.request.urlopen(req, timeout=180) as res:
    for line in res:
        line_str = line.decode().strip()
        if line_str.startswith("event:"):
            ev = line_str[6:].strip()
            elapsed = time.time() - t0
            print(f"[{elapsed:.1f}s] Event: {ev}")
        elif line_str.startswith("data:") and "run_id" in line_str:
            trace = json.loads(line_str[5:].strip())
            final_recs = trace.get("final", [])
            elapsed = time.time() - t0
            print(f"[{elapsed:.1f}s] Final trace completed! Movies returned: {len(final_recs)}")
            for item in final_recs:
                r = item.get("rank")
                t = item.get("title")
                y = item.get("year")
                fit = item.get("fit")
                reason = item.get("reason", "")[:60]
                print(f"   #{r} {t} ({y}) | Fit: {fit}")
                print(f"      Reason: {reason}...")
            break
