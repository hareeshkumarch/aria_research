"""Web fetch tool — extract text content from a URL."""
import time
import re


async def web_fetch(url: str, query: str = "") -> tuple[str, int]:
    """
    Fetch a URL and extract its text content.
    If a query is provided, uses an LLM to precisely extract the relevant information from the webpage.
    Returns (content, duration_ms).
    """
    import httpx
    import traceback

    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={
                "User-Agent": "ARIA Agent/1.0"
            })
            resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        text = resp.text

        # Basic HTML to text extraction
        if "html" in content_type:
            text = _html_to_text(text)

        # Truncate very long content before feeding to LLM
        if len(text) > 20000:
            text = text[:20000] + "\n\n[... content truncated ...]"

        # If a query is provided, use an LLM to extract the exact answer
        if query:
            try:
                from ...llm import get_llm
                from langchain_core.messages import SystemMessage, HumanMessage
                llm = get_llm()
                
                messages = [
                    SystemMessage(content=(
                        "You are a precise data extraction tool reading webpage text. "
                        "Your task is to answer the user's query perfectly based ONLY on the text below. "
                        "Do not include conversational filler. Keep the answer concise, accurate, and informative. "
                        "If the answer is NOT found in the text, simply say 'Information not found on this page.'"
                    )),
                    HumanMessage(content=f"Query: {query}\n\nWebpage Text:\n{text}")
                ]
                
                response = await llm.ainvoke(messages)
                text = f"**Extracted Answer for '{query}':**\n\n{response.content}"
            except Exception as llm_e:
                # Fallback to returning the raw text if LLM extraction fails
                from ...logger import get_logger
                get_logger(__name__).error(f"LLM extraction failed in web_fetch: {str(llm_e)}\n{traceback.format_exc()}")
                text = f"[LLM Extraction Failed - Returning raw text]\n\n{text}"

        duration_ms = int((time.time() - start) * 1000)
        return text, duration_ms

    except httpx.TimeoutException as e:
        duration_ms = int((time.time() - start) * 1000)
        return f"Failed to fetch URL: Connection Timeout ({str(e)})", duration_ms
    except httpx.RequestError as e:
        duration_ms = int((time.time() - start) * 1000)
        return f"Failed to fetch URL: Request Error ({str(e)})", duration_ms
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        from ...logger import get_logger
        get_logger(__name__).error(f"Unexpected error in web_fetch: {str(e)}\n{traceback.format_exc()}")
        return f"Failed to fetch URL ({type(e).__name__}): {str(e)}", duration_ms


def _html_to_text(html: str) -> str:
    """Basic HTML to text — strip tags, decode entities."""
    # Remove script, style, meta, noscript, etc.
    html = re.sub(r'<(script|style|meta|noscript|header|footer|nav)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # Replace common block elements with newlines for better readable paragraphs
    html = re.sub(r'<(p|div|br|li|h[1-6]|tr)[^>]*>', '\n', html, flags=re.IGNORECASE)
    # Remove tags
    text = re.sub(r'<[^>]+>', ' ', html)
    # Decode common entities
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Rough paragraph breaks
    text = re.sub(r'  +', '\n\n', text)
    return text
