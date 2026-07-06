import logging
from typing import List

from backend.config import settings

logger = logging.getLogger("smartrfp.tools")


class TavilyTool:
    def __init__(self):
        self.api_key = settings.TAVILY_API_KEY
        self._client = None
        if self.api_key:
            try:
                from tavily import TavilyClient
                self._client = TavilyClient(api_key=self.api_key)
            except Exception as exc:
                logger.warning("TAVILY_API_KEY is set but the Tavily client "
                                "could not be initialised: %s", exc)

    @property
    def available(self) -> bool:
        return self._client is not None

    def search(self, query: str, max_results: int = 3) -> List[str]:
        if not self._client:
            return []
        try:
            res = self._client.search(query=query, max_results=max_results)
            return [r.get("content", "")[:300] for r in res.get("results", []) if r.get("content")]
        except Exception as exc:
            logger.warning("Tavily search failed: %s", exc)
            return []