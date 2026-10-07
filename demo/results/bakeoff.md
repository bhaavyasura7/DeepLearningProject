# CineMind Model Bake-off Report

**Evaluated on:** Apple Silicon (macOS) with Ollama structured output

| Model | Schema Valid Rate | Accuracy (24 Cases) | Avg Sec/Call | Memory |
| :--- | :---: | :---: | :---: | :---: |
| `qwen3:8b` | 100.0% | 95.8% (23/24) | 17.27s | 5.6 |

**Selected Winner:** `qwen3:8b`

- High schema adherence under strict JSON schema constraints.
- Reliable adherence to negative constraints (e.g., 'no violence', 'no horror').
- Fast response time (17.27s per 10-candidate batch).
