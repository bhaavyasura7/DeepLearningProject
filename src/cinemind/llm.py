from typing import Any, Dict, Optional, Type, TypeVar
import json
import time
import httpx
from pydantic import BaseModel
from src.cinemind.config import settings

T = TypeVar("T", bound=BaseModel)

class StageFailed(Exception):
    """Raised when an LLM stage fails validation after retry."""
    pass

class LLMClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        stub: bool = False,
        stub_mode: str = "valid"
    ):
        self.base_url = (base_url or settings.ollama_url).rstrip("/")
        self.model = model or settings.llm_model
        self.timeout = timeout or settings.llm_timeout
        self.stub = stub or settings.llm_stub
        self.stub_mode = stub_mode  # "valid", "malformed", "out_of_set"
        self.call_count: int = 0
        self.total_seconds: float = 0.0

    def reset_stats(self) -> None:
        self.call_count = 0
        self.total_seconds = 0.0

    async def ping(self) -> bool:
        if self.stub:
            return True
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    async def generate_raw(self, prompt: str, schema_dict: Optional[Dict[str, Any]] = None, system: Optional[str] = None) -> str:
        self.call_count += 1
        t0 = time.time()
        try:
            if self.stub:
                return self._generate_stub(schema_dict)

            payload: Dict[str, Any] = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                }
            }
            if schema_dict:
                payload["format"] = schema_dict
            else:
                payload["format"] = "json"
            if system:
                payload["system"] = system

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(f"{self.base_url}/api/generate", json=payload)
                res.raise_for_status()
                data = res.json()
                response_text = data.get("response", "")
                return response_text
        finally:
            self.total_seconds += (time.time() - t0)

    async def generate(
        self,
        prompt: str,
        schema: Type[T],
        system: Optional[str] = None,
        max_retries: int = 1
    ) -> T:
        schema_dict = schema.model_json_schema()
        last_error: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            try:
                raw_text = await self.generate_raw(prompt, schema_dict=schema_dict, system=system)
                # Clean up if markdown code blocks wrapped json
                cleaned = raw_text.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                elif cleaned.startswith("```"):
                    cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()

                parsed_json = json.loads(cleaned)
                return schema.model_validate(parsed_json)
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    # Append error hint to prompt on retry
                    prompt += f"\n\nPrevious attempt failed schema validation: {str(e)}. Please output strict valid JSON matching the schema."
                    continue

        raise StageFailed(f"Stage generation failed after {max_retries + 1} attempts: {last_error}")

    def _generate_stub(self, schema_dict: Optional[Dict[str, Any]]) -> str:
        if self.stub_mode == "malformed":
            return "{ invalid_json: true, "

        # Check target schema title or properties to return realistic valid mock data
        schema_str = json.dumps(schema_dict or {})
        if "Profile" in schema_str or "summary" in schema_str:
            return json.dumps({
                "likes": ["Sci-Fi", "Complex narratives", "Christopher Nolan"],
                "dislikes": ["Mindless action", "Horror"],
                "constraints": ["Runtime under 150m"],
                "mood": "Thought-provoking and thrilling",
                "summary": "Enjoys mind-bending sci-fi narratives with deep themes and strong directorial vision."
            })
        elif "verdicts" in schema_str or "Verdict" in schema_str:
            # JudgeBatchOutput
            return json.dumps({
                "verdicts": [
                    {
                        "movie_id": 999999 if self.stub_mode == "out_of_set" else 1,
                        "match": True,
                        "fit": 0.95,
                        "reason": "Captivating mind-bending sci-fi with intelligent storytelling."
                    }
                ]
            })
        elif "Brief" in schema_str or "violations" in schema_str:
            return json.dumps({
                "strong": ["Inception", "Interstellar"],
                "violations": ["Transformers"],
                "notes": "Strong pool of speculative sci-fi and cerebral thrillers."
            })
        elif "RankModelOutput" in schema_str or "rankings" in schema_str:
            target_id = 999999 if self.stub_mode == "out_of_set" else 1
            return json.dumps({
                "rankings": [
                    {
                        "movie_id": target_id,
                        "reason": "Outstanding mind-bending sci-fi masterpiece perfectly matching user interests."
                    }
                ]
            })

        return "{}"

default_llm = LLMClient()
