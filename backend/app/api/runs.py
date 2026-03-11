import asyncio
import json
import uuid
from typing import Optional

import time

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from ..logger import get_logger
from ..agent.graph import run_agent
from ..repositories.runs_repo import create_run, update_run, get_run, list_runs, delete_run
from ..repositories.events_repo import save_run_event, get_run_events
from ..config import settings
from ..constants import PROVIDER_CATALOG


router = APIRouter()
logger = get_logger(__name__)

# ─── Run Manager ─────────────────────────────────────────────────────────────
class RunManager:
    def __init__(self):
        self._runs: dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def add_run(self, run_id: str, goal: str, queue: asyncio.Queue):
        async with self._lock:
            # Cleanup stale runs (older than 60 mins) to prevent bloat
            now = time.time()
            stale = [r_id for r_id, r_data in self._runs.items() if now - r_data.get("created_at", now) > 3600]
            for r_id in stale:
                self._runs.pop(r_id, None)

            if len(self._runs) >= settings.max_concurrent_runs:
                raise HTTPException(status_code=429, detail="Maximum concurrent runs reached. Please try again later.")

            self._runs[run_id] = {
                "goal": goal,
                "queue": queue,
                "paused": False,
                "aborted": False,
                "created_at": time.time()
            }

    async def get_run(self, run_id: str) -> dict | None:
        async with self._lock:
            return self._runs.get(run_id)

    async def remove_run(self, run_id: str):
        async with self._lock:
            self._runs.pop(run_id, None)

run_manager = RunManager()


# ─── Schemas ──────────────────────────────────────────────────────────────────

class CreateRunRequest(BaseModel):
    goal: str = Field(..., min_length=5, max_length=2000)
    mode: str = Field("fast", description="Execution mode: 'fast' or 'deep'")
    model: Optional[str] = Field(None, description="The LLM model to use")
    provider: Optional[str] = Field(None, description="The LLM provider to use")

    @field_validator('goal')
    def goal_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Goal cannot be empty or just whitespace')
        return v


class RunResponse(BaseModel):
    run_id: str
    goal: str
    status: str
    output: Optional[str] = None
    critic_score: Optional[float] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    total_cost: Optional[float] = None
    created_at: Optional[str] = None


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post("/runs", response_model=RunResponse, status_code=201)
async def create_run_endpoint(body: CreateRunRequest, background_tasks: BackgroundTasks):
    """Start a new ARIA run. Returns run_id immediately; stream via /runs/{id}/stream."""
    if body.provider and body.provider != "auto" and body.provider not in PROVIDER_CATALOG:
        raise HTTPException(status_code=400, detail={
            "error": f"Invalid provider: {body.provider}",
            "valid_providers": list(PROVIDER_CATALOG.keys())
        })

    if body.provider and body.provider != "auto" and body.model and body.model != "auto":
        valid_models = PROVIDER_CATALOG[body.provider]["models"]
        if body.model not in valid_models:
             raise HTTPException(status_code=400, detail={
                "error": f"Invalid model for provider {body.provider}",
                "valid_models": valid_models
             })

    run_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()

    # Add to run manager (raises 429 if full)
    await run_manager.add_run(run_id, body.goal.strip(), queue)

    # Persist to DB
    await create_run(run_id, body.goal.strip())

    # Run agent in background
    background_tasks.add_task(_run_and_update, run_id, body.goal.strip(), body.mode, queue, body.model, body.provider)

    return RunResponse(run_id=run_id, goal=body.goal, status="running")


@router.get("/runs/{run_id}/stream")
async def stream_run(run_id: str):
    """SSE endpoint — streams real-time agent events."""
    active = await run_manager.get_run(run_id)
    if not active:
        # Check if run exists in DB (already completed)
        run = await get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found.")
        raise HTTPException(status_code=410, detail="Run already completed. Use GET /runs/{id} for results.")

    queue: asyncio.Queue = active["queue"]

    async def event_generator():
        yield ": ARIA stream start\n\n"

        while True:
            try:
                # 5 second timeout to send heartbeat and keep connection alive
                event = await asyncio.wait_for(queue.get(), timeout=5.0)
            except asyncio.TimeoutError:
                yield "event: heartbeat\ndata: {}\n\n"
                continue

            if event is None:
                yield "event: done\ndata: {}\n\n"
                break

            event_type = event.get("type", "message")
            yield f"event: {event_type}\ndata: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/runs", response_model=list[RunResponse])
async def list_runs_endpoint(limit: int = 50, offset: int = 0):
    """List all runs (history) from database."""
    runs = await list_runs(limit=limit, offset=offset)
    return [
        RunResponse(
            run_id=r["id"],
            goal=r["goal"],
            status=r["status"],
            output=r.get("final_output"),
            critic_score=r.get("critic_score"),
            total_tokens=r.get("total_tokens"),
            input_tokens=r.get("input_tokens"),
            output_tokens=r.get("output_tokens"),
            total_cost=r.get("total_cost"),
            created_at=r.get("created_at"),
        )
        for r in runs
    ]


@router.get("/runs/{run_id}", response_model=RunResponse)
async def get_run_endpoint(run_id: str):
    """Get a specific run."""
    run = await get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    return RunResponse(
        run_id=run["id"],
        goal=run["goal"],
        status=run["status"],
        output=run.get("final_output"),
        critic_score=run.get("critic_score"),
        input_tokens=run.get("input_tokens"),
        output_tokens=run.get("output_tokens"),
        total_tokens=run.get("total_tokens"),
        total_cost=run.get("total_cost"),
        created_at=run.get("created_at"),
    )


@router.delete("/runs/{run_id}")
async def delete_run_endpoint(run_id: str):
    """Delete a run and all its data."""
    run = await get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    await delete_run(run_id)
    return {"message": "Run deleted."}


@router.get("/runs/{run_id}/events")
async def get_events_endpoint(run_id: str):
    """Get all events for a run (for replay)."""
    run = await get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    events = await get_run_events(run_id)
    return events


# ─── Background helper ────────────────────────────────────────────────────────

async def _run_and_update(run_id: str, goal: str, mode: str, queue: asyncio.Queue, model: Optional[str] = None, provider: Optional[str] = None):
    """Wrapper that updates run status in DB after agent completes."""
    start_time = time.time()
    # Collect all events for persistence
    original_put = queue.put
    collected_output = []  # Collect token events to build final output
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0
    total_cost = 0.0
    critic_score = 0.0
    run_had_error = False

    async def intercepting_put(event):
        nonlocal input_tokens, output_tokens, total_tokens, total_cost, critic_score, run_had_error
        await original_put(event)
        if event and isinstance(event, dict):
            # Collect token content for final output
            if event.get("type") == "token" and event.get("content"):
                collected_output.append(event["content"])
            # Capture cost updates
            if event.get("type") == "cost_update":
                input_tokens = event.get("input_tokens", input_tokens)
                output_tokens = event.get("output_tokens", output_tokens)
                total_tokens = input_tokens + output_tokens
                total_cost = event.get("total_cost", event.get("cost", total_cost))
            # Capture critic score
            if event.get("type") == "critic_score":
                critic_score = event.get("score", critic_score)
            # Detect errors from within the graph
            if event.get("type") == "run_error":
                run_had_error = True
            # Capture final cost_data from run_complete for accuracy
            if event.get("type") == "run_complete":
                cost_data = event.get("cost_data", {})
                if cost_data:
                    input_tokens = cost_data.get("input_tokens", input_tokens)
                    output_tokens = cost_data.get("output_tokens", output_tokens)
                    total_tokens = input_tokens + output_tokens
                    total_cost = cost_data.get("total_cost", total_cost)
                if event.get("critic_score"):
                    critic_score = event.get("critic_score", critic_score)
            try:
                await save_run_event(
                    run_id=run_id,
                    event_type=event.get("type", ""),
                    node=event.get("node", ""),
                    payload=json.dumps(event),
                )
            except Exception as e:
                logger.warning(f"Failed to save run event: {e}")

    queue.put = intercepting_put

    try:
        await run_agent(goal, run_id, queue, mode, model, provider)
    except Exception as e:
        import traceback
        run_had_error = True
        logger.error(f"Agent crashed unexpectedly: {e}\n{traceback.format_exc()}")
        await queue.put({
            "type": "run_error",
            "error": f"Agent crashed unexpectedly: {str(e)}",
            "run_id": run_id
        })
    finally:
        # Calculate final metrics
        duration_ms = int((time.time() - start_time) * 1000)
        # Update DB with final status, output, AND full metrics
        try:
            from datetime import datetime, timezone
            final_output = "".join(collected_output)
            final_status = "error" if run_had_error else "completed"
            await update_run(
                run_id,
                status=final_status,
                final_output=final_output,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                total_cost=total_cost,
                critic_score=critic_score,
                completed_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as e:
            logger.warning(f"Failed to update run final status: {e}")

        # Emit metrics AFTER DB update so the frontend can refresh history reliably.
        await queue.put({
            "type": "metrics_update",
            "duration_ms": duration_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "run_id": run_id,
        })

        # Send termination signal
        await queue.put(None)

        # Clean up active runs after a delay
        await asyncio.sleep(5)
        await run_manager.remove_run(run_id)


