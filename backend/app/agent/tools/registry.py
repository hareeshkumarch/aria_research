"""Tool registry — maps tool names to functions + availability + validation.

This module intentionally stays lightweight: it only exposes metadata and a
simple validation helper. All logging is centralized through the app logger.
"""
from .web_search import web_search
from .web_fetch import web_fetch
from .file_ops import read_file, write_file
from .code_exec import code_exec
from .memory_tools import recall_memory, store_memory
from ...config import settings
from ...logger import get_logger

logger = get_logger(__name__)


TOOL_REGISTRY = {
    "web_search": {
        "fn": web_search,
        "description": "Search the web for information",
        "available": True,  # Always available (DDG is free)
        "parameters": {"query": "str", "max_results": "int"},
        "expected_output": "Markdown-formatted search results with titles, snippets, and source URLs",
    },
    "web_fetch": {
        "fn": web_fetch,
        "description": "Fetch and extract content from a URL. If a query is provided, it returns only the exact information requested using an LLM.",
        "available": True,
        "parameters": {"url": "str", "query": "str (optional)"},
        "expected_output": "Extracted text content from the URL, or precise answer derived from the page if query is provided",
    },
    "read_file": {
        "fn": read_file,
        "description": "Read a file from the outputs directory",
        "available": True,
        "parameters": {"filepath": "str"},
        "expected_output": "File content as text",
    },
    "write_file": {
        "fn": write_file,
        "description": "Write content to a file in the outputs directory",
        "available": True,
        "parameters": {"filepath": "str", "content": "str"},
        "expected_output": "Success confirmation with character count",
    },
    "code_exec": {
        "fn": code_exec,
        "description": "Execute Python code in a sandboxed environment",
        "available": bool(settings.e2b_api_key),
        "parameters": {"code": "str", "language": "str"},
        "expected_output": "Code execution output (stdout, stderr, results)",
    },
    "recall_memory": {
        "fn": recall_memory,
        "description": "Search ARIA's memory for relevant past findings",
        "available": True,
        "parameters": {"query": "str", "n_results": "int"},
        "expected_output": "Formatted past research findings with relevance scores",
    },
    "store_memory": {
        "fn": store_memory,
        "description": "Store a finding in ARIA's persistent memory",
        "available": True,
        "parameters": {"text": "str", "run_id": "str", "goal": "str"},
        "expected_output": "Confirmation with stored chunk ID",
    },
}

# Error patterns that indicate a failed tool response
# Checked only against the first line of the result to avoid false positives.
_ERROR_PATTERNS = [
    "search failed",
    "no results found",
    "failed to fetch",
    "tool error",
    "code execution failed",
    "file not found",
    "file read failed",
    "file write failed",
    "memory recall failed",
    "memory store failed",
    "not available",
]

# Minimum content length to consider a result valid (per tool)
_MIN_CONTENT_LENGTH = {
    "web_search": 50,
    "web_fetch": 100,
    "recall_memory": 10,
    "code_exec": 5,
    "read_file": 1,
    "write_file": 5,
    "store_memory": 5,
}


def get_tool(name: str):
    """Get a tool function by name."""
    entry = TOOL_REGISTRY.get(name)
    if not entry:
        logger.warning("Requested unknown tool: %s", name)
        return None
    return entry["fn"]


def get_available_tools() -> dict:
    """Return all tools with their availability status and metadata."""
    return {
        name: {
            "description": info["description"],
            "available": info["available"],
            "parameters": info.get("parameters", {}),
            "expected_output": info.get("expected_output", ""),
        }
        for name, info in TOOL_REGISTRY.items()
    }


def is_tool_available(name: str) -> bool:
    """Check if a tool is available."""
    entry = TOOL_REGISTRY.get(name)
    if not entry:
        logger.warning("Checked availability for unknown tool: %s", name)
        return False
    return bool(entry["available"])


def validate_tool_result(tool_name: str, result: str) -> tuple[bool, str]:
    """
    Validate a tool's response before passing to the next node.
    Returns (is_valid, message).
    """
    if not result:
        return False, "Empty result"

    # Check for error patterns on the first line only (to avoid matching quoted text)
    first_line = result.strip().splitlines()[0].lower()
    for pattern in _ERROR_PATTERNS:
        if first_line.startswith(pattern):
            return False, f"Error pattern detected: '{pattern}'"

    # Check minimum content length
    min_len = _MIN_CONTENT_LENGTH.get(tool_name, 10)
    if len(result.strip()) < min_len:
        return False, f"Result too short ({len(result.strip())} chars, minimum {min_len})"

    return True, "Valid"
