from typing import Optional, List
from src.cinemind.cache import ProfileCache
from src.cinemind.llm import LLMClient, default_llm
from src.cinemind.schemas import Rated, Profile

class EmptyInput(Exception):
    """Raised when both history and query are empty."""
    pass

class UnderstandingAgent:
    def __init__(self, llm: Optional[LLMClient] = None, cache: Optional[ProfileCache] = None):
        self.llm = llm or default_llm
        self.cache = cache or ProfileCache()

    async def understand(
        self,
        history: Optional[List[Rated]] = None,
        query: Optional[str] = None
    ) -> Profile:
        has_history = bool(history and len(history) > 0)
        has_query = bool(query and query.strip())

        if not has_history and not has_query:
            raise EmptyInput("Empty query and empty history. At least one must be provided.")

        cache_key = self.cache.compute_key(history, query)
        cached = self.cache.get(cache_key)
        if cached:
            return Profile.model_validate(cached)

        # Build prompt
        prompt = (
            "You are the Understanding stage of CineMind, an expert cinematic recommendation engine.\n"
            "Analyze the viewer's explicit query and/or viewing history to produce a structured Profile.\n"
            "Extract likes (genres, themes, directors, tropes), dislikes, negative constraints (e.g. 'no horror', 'runtime under 2h'), "
            "emotional mood, and a concise 1-2 sentence semantic summary.\n\n"
        )

        if has_query:
            prompt += f"USER QUERY: \"{query.strip()}\"\n\n"

        if has_history:
            # Most recent 30 movies
            sorted_history = sorted(
                history,
                key=lambda x: (x.timestamp or 0),
                reverse=True
            )[:30]
            prompt += "VIEWER WATCH HISTORY (Movie, Rating, Genres):\n"
            for item in sorted_history:
                title_str = item.title or f"Movie {item.movie_id}"
                genres_str = f" ({', '.join(item.genres)})" if item.genres else ""
                prompt += f"- {title_str}{genres_str}: rated {item.rating}/5.0\n"
            prompt += "\n"

        prompt += "Return a valid JSON matching the Profile schema with likes, dislikes, constraints, mood, and summary."

        profile: Profile = await self.llm.generate(prompt, Profile)
        self.cache.set(cache_key, profile.model_dump())
        return profile
