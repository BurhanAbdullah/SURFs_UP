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
