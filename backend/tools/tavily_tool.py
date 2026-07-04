"""
backend/tools/tavily_tool.py — TavilyTool.

Thin wrapper around the Tavily web-search API for live market/pricing
insight. This file did not exist even though
backend/services/estimation_service.py has always imported it
(`from backend.tools.tavily_tool import TavilyTool`), which meant importing
backend.services — and therefore backend.main — crashed with
`ModuleNotFoundError: No module named 'backend.tools'`.

Fully optional: with no TAVILY_API_KEY configured (or the `tavily` package
not installed), `.available` is False and `.search()` returns an empty list
rather than raising, so nothing that depends on this tool breaks without it.
Mirrors the same optional-Tavily pattern already used in
agents/pricing_agent.py.
"""
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
            except Exception as exc:  # noqa: BLE001
                logger.warning("TAVILY_API_KEY is set but the Tavily client "
                                "could not be initialised: %s", exc)

    @property
    def available(self) -> bool:
        return self._client is not None

    def search(self, query: str, max_results: int = 3) -> List[str]:
        """Return a list of short text snippets, or [] if unavailable/failed."""
        if not self._client:
            return []
        try:
            res = self._client.search(query=query, max_results=max_results)
            return [r.get("content", "")[:300] for r in res.get("results", []) if r.get("content")]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Tavily search failed: %s", exc)
            return []