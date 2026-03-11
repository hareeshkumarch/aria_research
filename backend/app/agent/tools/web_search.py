"""Web search tool — DuckDuckGo (default) + Tavily (optional).

All paths return a simple `(text, duration_ms)` tuple and log through the
standard app logger so that failures are easy to trace in one place.
"""
import asyncio
import time
import importlib.util
import json
from concurrent.futures import ThreadPoolExecutor

from ...config import settings
from ...logger import get_logger

logger = get_logger(__name__)
_executor = ThreadPoolExecutor(max_workers=10)


def _normalize_query(raw: str) -> str:
    """
    Normalize planner/tool queries into a plain text search string.
    
    Handles cases where the query is a JSON-encoded list/dict like:
    [
      {"title": "...", "query": "...", "description": "..."}
    ]
    so that DuckDuckGo receives a meaningful text query instead of the raw JSON.
    """
    text = (raw or "").strip()
    if not text:
        return text

    # Try to parse JSON and extract useful fields
    try:
        data = json.loads(text)
    except Exception:
        return text

    parts: list[str] = []

    def _collect(obj):
        if not isinstance(obj, dict):
            return
        for key in ("query", "title", "description"):
            val = obj.get(key)
            if isinstance(val, str) and val.strip():
                parts.append(val.strip())

    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                _collect(item)
    elif isinstance(data, dict):
        _collect(data)

    return " — ".join(dict.fromkeys(parts)) if parts else text

def _sync_ddg_search(query: str, max_results: int = 5) -> str:
    """Synchronous DuckDuckGo search using duckduckgo-search package."""
    try:
        # Use the installed DuckDuckGo search client from the duckduckgo-search package
        from duckduckgo_search import DDGS  # pyright: ignore[reportMissingImports]
        ddgs = DDGS()
        results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return f"No results found for: {query}"

        parts = []
        for r in results:
            title = r.get("title", "No title").strip()
            body = r.get("body", "").strip()
            href = r.get("href", "").strip()
            parts.append(f"### [{title}]({href})\n{body}\n**Source:** {href}")

        return "\n\n---\n\n".join(parts)

    except Exception as e:
        import traceback
        logger.error("DuckDuckGo search failed: %s\n%s", str(e), traceback.format_exc())
        return f"Search failed ({type(e).__name__}): {str(e)}"


def _sync_tavily_search(query: str, max_results: int = 5) -> str:
    """Tavily search — if API key is available."""
    try:
        from tavily import TavilyClient  # pyright: ignore[reportMissingImports]
        client = TavilyClient(api_key=settings.tavily_api_key)
        response = client.search(query=query, max_results=max_results)

        parts = []
        for r in response.get("results", []):
            title = r.get("title", "No title").strip()
            content = r.get("content", "").strip()
            url = r.get("url", "").strip()
            parts.append(f"### [{title}]({url})\n{content}\n**Source:** {url}")

        return "\n\n---\n\n".join(parts) if parts else f"No results found for: {query}"
    except Exception as e:
        import traceback
        logger.error("Tavily search failed: %s\n%s", str(e), traceback.format_exc())
        return f"Tavily search failed ({type(e).__name__}): {str(e)}"


async def web_search(query: str, max_results: int = 5) -> tuple[str, int]:
    """
    Async web search. Uses Tavily if API key available, else DuckDuckGo.
    Returns (result_text, duration_ms).
    
    Includes retry with exponential backoff (up to 3 attempts).
    """
    loop = asyncio.get_event_loop()

    # Defensive: planner sometimes sends JSON-encoded objects instead of plain text.
    # Normalize those into a clean textual query so search actually returns results.
    normalized_query = _normalize_query(query)

    # Choose search backend (all implementations are sync; we offload to a thread)
    search_fn = _sync_ddg_search
    if settings.tavily_api_key and importlib.util.find_spec("tavily"):
        search_fn = _sync_tavily_search
    elif settings.tavily_api_key:
        logger.warning("Tavily API key configured but 'tavily' package is not installed. Falling back to DuckDuckGo.")

    # Retry with exponential backoff (up to 4 attempts)
    last_error = ""
    for attempt in range(4):
        start = time.time()
        try:
            result = await loop.run_in_executor(
                _executor, search_fn, normalized_query, max_results
            )
            duration_ms = int((time.time() - start) * 1000)

            if "Search failed" not in result and "Tavily search failed" not in result:
                # Success
                return result, duration_ms
            else:
                last_error = result
                logger.warning("Web search attempt %d failed: %s", attempt + 1, result)

        except Exception as e:
            logger.error("Web search executor error attempt %d: %s", attempt + 1, str(e))
            last_error = f"Search error ({type(e).__name__}): {str(e)}"

        # Exponential backoff
        if attempt < 3:
            # 1s, 2s, 4s delays
            await asyncio.sleep(2 ** attempt)

    return f"All search attempts failed. Last error: {last_error}", 0
