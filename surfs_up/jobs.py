"""Persistent filesystem queue for long-running SURF web jobs."""

from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

from surfs_up.core import SimulationRequest, run_generated_code
from surfs_up.core.codegen import build_generated_code


JOB_DIR = Path(
    os.environ.get("SURFS_UP_JOB_DIR", Path.home() / ".cache" / "surfs_up" / "jobs")
)


def _job_path(job_id: str) -> Path:
    if not job_id.isalnum():
        raise ValueError("Invalid job ID")
    return JOB_DIR / f"{job_id}.json"


def _queue_path(job_id: str, state: str = "pending") -> Path:
    return JOB_DIR / state / f"{job_id}.json"


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
    ) as handle:
        json.dump(value, handle)
        temporary = Path(handle.name)
    temporary.replace(path)


def enqueue(simulation: SimulationRequest, owner_session_id: str) -> str:
    """Persist a validated job and make it visible to the worker."""
    job_id = uuid.uuid4().hex
    now = time.time()
    status = {
        "id": job_id,
        "owner_session_id": owner_session_id,
        "state": "pending",
        "message": "Queued for processing",
        "created_at": now,
        "updated_at": now,
    }
    payload = {
        "id": job_id,
        "owner_session_id": owner_session_id,
        "simulation": simulation.to_dict(),
    }
    _write_json(_job_path(job_id), status)
    _write_json(_queue_path(job_id), payload)
    return job_id


def read_status(job_id: str) -> dict[str, Any] | None:
    """Read the latest public status for a job."""
    try:
        return json.loads(_job_path(job_id).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
        return None


def update_status(job_id: str, **changes: Any) -> dict[str, Any]:
    """Atomically update a job's status document."""
    status = read_status(job_id)
    if status is None:
        raise FileNotFoundError(job_id)
    status.update(changes, updated_at=time.time())
    _write_json(_job_path(job_id), status)
    return status


def _claim_next() -> tuple[Path, dict[str, Any]] | None:
    """Atomically claim one queued job."""
    pending_dir = JOB_DIR / "pending"
    working_dir = JOB_DIR / "working"
    working_dir.mkdir(parents=True, exist_ok=True)
    for pending in sorted(pending_dir.glob("*.json")) if pending_dir.exists() else ():
        working = working_dir / pending.name
        try:
            pending.replace(working)
            return working, json.loads(working.read_text(encoding="utf-8"))
        except FileNotFoundError:
            continue
    return None


def process_one() -> bool:
    """Run one queued job, returning whether a job was claimed."""
    claimed = _claim_next()
    if claimed is None:
        return False
    working_path, payload = claimed
    job_id = str(payload["id"])
    try:
        simulation_data = payload["simulation"]
        simulation = SimulationRequest.from_mappings(
            simulation_data["model"],
            simulation_data["ambient"],
            simulation_data.get("cmes"),
        )
        code = build_generated_code(simulation)
        update_status(job_id, state="running", message="Grabbing and processing input data")
        result = run_generated_code(
            code,
            before_solve=lambda: update_status(
                job_id, state="running", message="Running SURF"
            ),
            on_chunk=lambda current, total: update_status(
                job_id,
                state="running",
                message=f"Running SURF — chunk {current} of {total}",
            ),
        )
        if result.success and result.model is not None:
            # Imported lazily to avoid loading the Flask adapter in queue-only callers.
            from surfs_up.web.app import _write_run_cache

            retained = {
                "model": result.model,
                "simulation": simulation,
                "owner_session_id": payload["owner_session_id"],
            }
            if not _write_run_cache(job_id, retained):
                raise RuntimeError("The completed model could not be saved to the run cache.")
            update_status(
                job_id,
                state="completed",
                message=result.message,
                output=result.output,
                show_movies=not bool(simulation.model.get("is_1d", False)),
            )
        else:
            update_status(
                job_id,
                state="failed",
                message=result.message,
                output=result.output,
            )
    except Exception as exc:
        import traceback

        update_status(
            job_id,
            state="failed",
            message=f"SURF run failed: {exc}",
            output=traceback.format_exc(),
        )
    finally:
        working_path.unlink(missing_ok=True)
    return True


def _recover_interrupted_jobs() -> None:
    """Requeue jobs left claimed when a previous worker was stopped."""
    working_dir = JOB_DIR / "working"
    pending_dir = JOB_DIR / "pending"
    if not working_dir.exists():
        return
    pending_dir.mkdir(parents=True, exist_ok=True)
    for working in working_dir.glob("*.json"):
        try:
            working.replace(pending_dir / working.name)
            update_status(
                working.stem,
                state="pending",
                message="Queued again after worker restart",
            )
        except FileNotFoundError:
            continue


def run_worker(poll_interval: float = 2.0, once: bool = False) -> None:
    """Continuously process queued jobs for an Always-on Task."""
    from surfs_up.web.app import _prune_run_cache

    _prune_run_cache()
    _recover_interrupted_jobs()
    while True:
        try:
            processed = process_one()
        finally:
            _prune_run_cache()
        if once:
            return
        if not processed:
            time.sleep(poll_interval)


def main() -> None:
    """Console entry point for the persistent job worker."""
    run_worker()


if __name__ == "__main__":
    main()
