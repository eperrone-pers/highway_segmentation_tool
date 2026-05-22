import json

import pytest

import run_tests


pytestmark = pytest.mark.unit


def test_write_matrix_summary_includes_progress_metadata(tmp_path):
    results = [
        {
            "lane": "smoke",
            "status": "PASS",
            "duration_seconds": 1.25,
        }
    ]

    summary_path = run_tests.write_matrix_summary(
        results,
        tmp_path,
        lane_names=["smoke", "regression"],
        run_status="running",
        current_lane="regression",
    )

    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["run_status"] == "running"
    assert payload["current_lane"] == "regression"
    assert payload["planned_lanes"] == ["smoke", "regression"]
    assert payload["completed_lane_count"] == 1
    assert payload["results"] == results


def test_run_matrix_updates_summary_after_each_lane(tmp_path, monkeypatch):
    lane_names = ["smoke", "ui"]
    lane_specs = {
        "smoke": {"description": "Smoke"},
        "ui": {"description": "UI"},
    }
    lane_results = {
        "smoke": {"lane": "smoke", "status": "PASS", "duration_seconds": 1.0, "note": ""},
        "ui": {"lane": "ui", "status": "PASS", "duration_seconds": 2.0, "note": ""},
    }
    summary_calls = []
    original_write_matrix_summary = run_tests.write_matrix_summary

    def fake_run_lane(lane_name, lane_spec, *, log_dir, continue_on_failure=False):
        return lane_results[lane_name]

    def tracking_write_matrix_summary(results, log_dir, *, lane_names=None, run_status="completed", current_lane=None):
        summary_calls.append(
            {
                "results": [result["lane"] for result in results],
                "run_status": run_status,
                "current_lane": current_lane,
                "planned_lanes": list(lane_names or []),
            }
        )
        return original_write_matrix_summary(
            results,
            log_dir,
            lane_names=lane_names,
            run_status=run_status,
            current_lane=current_lane,
        )

    monkeypatch.setattr(run_tests, "run_lane", fake_run_lane)
    monkeypatch.setattr(run_tests, "write_matrix_summary", tracking_write_matrix_summary)
    monkeypatch.setattr(run_tests, "print_matrix_summary", lambda results, summary_path: None)

    run_tests.run_matrix(lane_names, lane_specs, tmp_path)

    assert summary_calls == [
        {
            "results": [],
            "run_status": "running",
            "current_lane": "smoke",
            "planned_lanes": ["smoke", "ui"],
        },
        {
            "results": ["smoke"],
            "run_status": "running",
            "current_lane": "ui",
            "planned_lanes": ["smoke", "ui"],
        },
        {
            "results": ["smoke", "ui"],
            "run_status": "completed",
            "current_lane": None,
            "planned_lanes": ["smoke", "ui"],
        },
    ]

    payload = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert payload["run_status"] == "completed"
    assert payload["current_lane"] is None
    assert payload["completed_lane_count"] == 2


def test_run_matrix_exits_nonzero_when_any_lane_fails(tmp_path, monkeypatch):
    lane_names = ["smoke", "regression"]
    lane_specs = {
        "smoke": {"description": "Smoke"},
        "regression": {"description": "Regression"},
    }
    lane_results = {
        "smoke": {"lane": "smoke", "status": "PASS", "duration_seconds": 1.0, "note": ""},
        "regression": {"lane": "regression", "status": "FAIL", "duration_seconds": 2.0, "note": "Return code 1"},
    }

    monkeypatch.setattr(
        run_tests,
        "run_lane",
        lambda lane_name, lane_spec, *, log_dir, continue_on_failure=False: lane_results[lane_name],
    )
    monkeypatch.setattr(run_tests, "print_matrix_summary", lambda results, summary_path: None)

    with pytest.raises(SystemExit) as exc_info:
        run_tests.run_matrix(lane_names, lane_specs, tmp_path)

    assert exc_info.value.code == 1
    payload = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert payload["run_status"] == "completed"
    assert payload["results"][-1]["status"] == "FAIL"