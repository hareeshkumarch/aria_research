"""Code execution tool — E2B Sandbox (optional, requires API key).

Kept intentionally simple: if E2B is not configured or installed, we return a
clear, non-fatal message and log the reason. On success/failure, everything is
routed through the shared logger.
"""
import time

from ...config import settings
from ...logger import get_logger

logger = get_logger(__name__)


async def code_exec(code: str, language: str = "python") -> tuple[str, int]:
    """
    Execute code in a sandboxed environment.
    Uses E2B if API key is available, otherwise returns unavailable message.
    Returns (output, duration_ms).
    """
    if not settings.e2b_api_key:
        msg = (
            "⚠ Code execution is not available — no E2B_API_KEY configured.\n"
            "Set E2B_API_KEY in your .env file to enable safe code execution.\n"
            "Get a free key at: https://e2b.dev"
        )
        logger.info("code_exec called without E2B_API_KEY; returning unavailable message.")
        return msg, 0

    start = time.time()
    try:
        from e2b_code_interpreter import CodeInterpreter

        with CodeInterpreter(api_key=settings.e2b_api_key) as sandbox:
            execution = sandbox.notebook.exec_cell(code)

            output_parts = []

            if execution.logs.stdout:
                output_parts.append("=== STDOUT ===\n" + "\n".join(execution.logs.stdout))

            if execution.logs.stderr:
                output_parts.append("=== STDERR ===\n" + "\n".join(execution.logs.stderr))

            if execution.results:
                for result in execution.results:
                    if hasattr(result, "text") and result.text:
                        output_parts.append("=== RESULT ===\n" + result.text)

            if execution.error:
                output_parts.append(f"=== ERROR ===\n{execution.error.name}: {execution.error.value}")

            output = "\n\n".join(output_parts) if output_parts else "Code executed successfully (no output)"

        duration_ms = int((time.time() - start) * 1000)
        return output, duration_ms

    except ImportError:
        logger.warning("code_exec requested but e2b-code-interpreter is not installed.")
        return "E2B SDK not installed. Run: pip install e2b-code-interpreter", 0
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        logger.error("Code execution failed: %s", str(e))
        return f"Code execution failed ({type(e).__name__}): {str(e)}", duration_ms
