"""Shared run context for the ARIA agent.

Uses ContextVars so queue, cost tracker, and pause/abort flags are all
**run-scoped** instead of global, which keeps concurrent runs isolated.
"""
import asyncio
from contextvars import ContextVar

# Queue for SSE events — set per-run, accessed by nodes
_queue_var: ContextVar[asyncio.Queue | None] = ContextVar("aria_queue", default=None)
_cost_tracker_var: ContextVar[object | None] = ContextVar("aria_cost_tracker", default=None)

# Pause/abort are tracked per-run in a shared registry keyed by run_id.
# This allows API control endpoints (pause/resume/abort) to affect the correct
# background task without relying on request-local ContextVars.
_run_controls: dict[str, dict[str, object]] = {}

# ContextVars remain useful for queue/cost-tracker (run-scoped within the task),
# but controls must be reachable cross-task → registry above.
_run_id_var: ContextVar[str | None] = ContextVar("aria_run_id", default=None)


def set_queue(queue: asyncio.Queue):
    _queue_var.set(queue)


def get_queue() -> asyncio.Queue | None:
    return _queue_var.get(None)


def set_cost_tracker(tracker: object | None):
    _cost_tracker_var.set(tracker)


def get_cost_tracker() -> object | None:
    return _cost_tracker_var.get(None)


def set_run_id(run_id: str):
    _run_id_var.set(run_id)


def get_run_id() -> str | None:
    return _run_id_var.get(None)


def register_run_controls(run_id: str, pause_event: asyncio.Event):
    _run_controls[run_id] = {"pause_event": pause_event, "aborted": False}


def unregister_run_controls(run_id: str):
    _run_controls.pop(run_id, None)


def pause_run(run_id: str):
    ctl = _run_controls.get(run_id)
    if not ctl:
        return
    ev = ctl.get("pause_event")
    if isinstance(ev, asyncio.Event):
        ev.clear()


def resume_run(run_id: str):
    ctl = _run_controls.get(run_id)
    if not ctl:
        return
    ev = ctl.get("pause_event")
    if isinstance(ev, asyncio.Event):
        ev.set()


def abort_run(run_id: str):
    ctl = _run_controls.get(run_id)
    if not ctl:
        return
    ctl["aborted"] = True
    # Ensure any paused run can proceed to observe abort.
    ev = ctl.get("pause_event")
    if isinstance(ev, asyncio.Event):
        ev.set()


def is_aborted(run_id: str) -> bool:
    ctl = _run_controls.get(run_id)
    if not ctl:
        return False
    return bool(ctl.get("aborted", False))


async def check_pause_and_abort(run_id: str | None = None):
    """Blocks if paused, raises if aborted (per run)."""
    rid = run_id or get_run_id()
    if not rid:
        return

    if is_aborted(rid):
        raise RuntimeError("Run aborted by user.")

    ctl = _run_controls.get(rid)
    ev = ctl.get("pause_event") if ctl else None
    if isinstance(ev, asyncio.Event):
        await ev.wait()

    if is_aborted(rid):
        raise RuntimeError("Run aborted by user.")
