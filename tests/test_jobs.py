"""Persistent background-job tests."""

from types import SimpleNamespace

from surfs_up.core import SimulationRequest


def _simulation() -> SimulationRequest:
    return SimulationRequest.from_mappings(
        {
            "solver": "huxt",
            "rmin": 21.5,
            "rmax": 240,
            "latitude": 0,
            "simtime_days": 5,
            "start_datetime": "2026-07-03 12:00",
            "cr_num": 2300,
            "cr_lon_init_deg": 0,
            "is_1d": True,
        },
        {"source": "user_specified", "speed_kms": 400},
    )


def test_worker_processes_persistent_job(monkeypatch, tmp_path):
    import surfs_up.jobs as jobs
    import surfs_up.web.app as web_app

    monkeypatch.setattr(jobs, "JOB_DIR", tmp_path / "jobs")
    monkeypatch.setattr(jobs, "build_generated_code", lambda simulation: "# generated")
    monkeypatch.setattr(
        jobs,
        "run_generated_code",
        lambda code, before_solve, on_chunk: (
            before_solve(),
            on_chunk(1, 1),
            SimpleNamespace(
                success=True,
                model=object(),
                message="SURF run completed successfully.",
                output="done",
            ),
        )[-1],
    )
    retained = {}
    monkeypatch.setattr(
        web_app,
        "_write_run_cache",
        lambda run_id, value: (retained.update({run_id: value}), True)[1],
    )

    job_id = jobs.enqueue(_simulation(), "browser-session")
    assert jobs.read_status(job_id)["state"] == "pending"

    assert jobs.process_one() is True
    status = jobs.read_status(job_id)
    assert status["state"] == "completed"
    assert status["output"] == "done"
    assert status["show_movies"] is False
    assert retained[job_id]["owner_session_id"] == "browser-session"
    assert jobs.process_one() is False


def test_async_submission_returns_job_and_owner_only_status(monkeypatch, tmp_path):
    import surfs_up.jobs as jobs
    import surfs_up.web.app as web_app

    monkeypatch.setattr(jobs, "JOB_DIR", tmp_path / "jobs")
    monkeypatch.setattr(web_app, "enqueue", jobs.enqueue)
    monkeypatch.setattr(web_app, "read_status", jobs.read_status)
    app = web_app.create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "job-test-secret",
            "RUN_JOBS_SYNCHRONOUS": False,
        }
    )
    client = app.test_client()
    response = client.post(
        "/",
        data={
            "action": "run",
            "ambient_source": "user_specified",
            "solver": "huxt",
            "rmin": "21.5",
            "rmax": "240",
            "latitude": "0",
            "simtime_days": "5",
            "speed_kms": "400",
            "start_datetime": "2026-07-03T12:00",
            "cr_num": "2300",
            "cr_lon_init_deg": "0",
        },
    )

    assert response.status_code == 202
    payload = response.get_json()
    status = client.get(payload["status_url"])
    assert status.status_code == 200
    assert status.get_json()["state"] == "pending"

    other_browser = app.test_client()
    assert other_browser.get(payload["status_url"]).status_code == 404


def test_new_job_cancels_only_same_owners_pending_job(monkeypatch, tmp_path):
    import surfs_up.jobs as jobs

    monkeypatch.setattr(jobs, "JOB_DIR", tmp_path / "jobs")
    old_job = jobs.enqueue(_simulation(), "browser-session")
    other_job = jobs.enqueue(_simulation(), "other-session")

    new_job = jobs.enqueue(_simulation(), "browser-session")

    old_status = jobs.read_status(old_job)
    assert old_status["state"] == "failed"
    assert old_status["cancel_requested"] is True
    assert not jobs._queue_path(old_job).exists()
    assert jobs.read_status(other_job)["state"] == "pending"
    assert jobs._queue_path(other_job).exists()
    assert jobs.read_status(new_job)["state"] == "pending"


def test_worker_does_not_complete_a_cancelled_running_job(monkeypatch, tmp_path):
    import surfs_up.jobs as jobs

    monkeypatch.setattr(jobs, "JOB_DIR", tmp_path / "jobs")
    monkeypatch.setattr(jobs, "build_generated_code", lambda simulation: "# generated")
    first_job = jobs.enqueue(_simulation(), "browser-session")

    def run_generated_code(code, before_solve, on_chunk):
        before_solve()
        jobs.enqueue(_simulation(), "browser-session")
        on_chunk(1, 1)
        raise AssertionError("cancelled callback should stop the old run")

    monkeypatch.setattr(jobs, "run_generated_code", run_generated_code)
    assert jobs.process_one() is True
    status = jobs.read_status(first_job)
    assert status["state"] == "failed"
    assert status["message"] == "Cancelled because a newer run was submitted"


def test_worker_restart_does_not_requeue_cancelled_work(monkeypatch, tmp_path):
    import surfs_up.jobs as jobs

    monkeypatch.setattr(jobs, "JOB_DIR", tmp_path / "jobs")
    old_job = jobs.enqueue(_simulation(), "browser-session")
    claimed = jobs._claim_next()
    assert claimed is not None
    working_path, _ = claimed

    jobs.enqueue(_simulation(), "browser-session")
    jobs._recover_interrupted_jobs()

    assert not working_path.exists()
    assert not jobs._queue_path(old_job).exists()
    assert jobs.read_status(old_job)["state"] == "failed"


def test_local_restart_discards_all_unfinished_jobs(monkeypatch, tmp_path):
    import surfs_up.jobs as jobs

    monkeypatch.setattr(jobs, "JOB_DIR", tmp_path / "jobs")
    pending_job = jobs.enqueue(_simulation(), "first-session")
    working_job = jobs.enqueue(_simulation(), "second-session")
    claimed = jobs._claim_next()
    assert claimed is not None

    jobs.cancel_all_unfinished_jobs()

    for job_id in (pending_job, working_job):
        assert jobs.read_status(job_id)["state"] == "failed"
        assert not jobs._queue_path(job_id).exists()
        assert not jobs._queue_path(job_id, "working").exists()
