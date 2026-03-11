"""Run controls — pause, resume, abort."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from .runs import run_manager
from ..agent.context import pause_run as pause_agent_run, resume_run as resume_agent_run, abort_run as abort_agent_run


router = APIRouter()


class ResumeRequest(BaseModel):
    directive: Optional[str] = None  # Optional override instructions


@router.post("/runs/{run_id}/pause")
async def pause_run(run_id: str):
    """Pause a running agent."""
    active = await run_manager.get_run(run_id)
    if not active:
        raise HTTPException(status_code=404, detail="Run not found or not active.")

    active["paused"] = True
    pause_agent_run(run_id)  # Actually block the agent pipeline for this run

    # Emit pause event
    queue = active["queue"]
    await queue.put({"type": "run_paused", "run_id": run_id})

    return {"message": "Run paused.", "run_id": run_id}


@router.post("/runs/{run_id}/resume")
async def resume_run_endpoint(run_id: str, body: ResumeRequest = None):
    """Resume a paused agent, optionally with a new directive."""
    active = await run_manager.get_run(run_id)
    if not active:
        raise HTTPException(status_code=404, detail="Run not found or not active.")

    active["paused"] = False
    resume_agent_run(run_id)  # Unblock the agent pipeline for this run

    directive_msg = ""
    if body and body.directive:
        directive_msg = f" with directive: {body.directive}"

    queue = active["queue"]
    await queue.put({
        "type": "run_resumed",
        "run_id": run_id,
        "directive": body.directive if body else None,
    })

    return {"message": f"Run resumed{directive_msg}.", "run_id": run_id}


@router.post("/runs/{run_id}/abort")
async def abort_run(run_id: str):
    """Abort a running agent."""
    active = await run_manager.get_run(run_id)
    if not active:
        raise HTTPException(status_code=404, detail="Run not found or not active.")

    active["aborted"] = True
    abort_agent_run(run_id)  # Mark aborted and unblock if paused so abort check can fire

    queue = active["queue"]
    await queue.put({"type": "run_aborted", "run_id": run_id})
    await queue.put(None)  # Close the SSE stream

    return {"message": "Run aborted.", "run_id": run_id}
