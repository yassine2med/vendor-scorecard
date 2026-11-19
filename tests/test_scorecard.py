from pathlib import Path

import pytest

from vendorscore import build_scorecard, component_scores, grade, load_jobs
from vendorscore.cli import main

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "vendor_jobs.csv"
HEADER = "wo_id,vendor,due_date,completed_date,reopened,estimate,actual_cost\n"


def jobs(tmp_path, body):
    path = tmp_path / "jobs.csv"
    path.write_text(HEADER + body)
    return load_jobs(path)


def test_grade_boundaries():
    assert [grade(s) for s in (100, 90, 89.9, 80, 70, 60, 59.9, 0)] == ["A", "A", "B", "B", "C", "D", "F", "F"]


def test_component_scores_perfect():
    assert component_scores(1.0, 0.0, -0.1) == {"on_time": 100.0, "reopen": 100.0, "cost": 100.0}


def test_component_scores_floor_and_cap():
    parts = component_scores(0.5, 0.40, 0.50)
    assert parts == {"on_time": 50.0, "reopen": 0.0, "cost": 0.0}


def test_component_scores_midpoint():
    parts = component_scores(0.9, 0.10, 0.125)
    assert parts["reopen"] == pytest.approx(50.0) and parts["cost"] == pytest.approx(50.0)


def test_scorecard_values(tmp_path):
    df = jobs(tmp_path, (
        "1,Acme HVAC,2026-03-01,2026-03-01,no,100,100\n"
        "2,Acme HVAC,2026-03-02,2026-03-05,yes,100,110\n"
        "3,Bolt Electric,2026-03-02,2026-03-01,no,200,190\n"
    ))
    card = build_scorecard(df, min_jobs=2).set_index("vendor")
    acme = card.loc["Acme HVAC"]
    assert acme["on_time_pct"] == 50.0 and acme["reopen_pct"] == 50.0 and acme["cost_var_pct"] == 5.0
    assert acme["score"] == pytest.approx(0.5 * 50 + 0.3 * 0 + 0.2 * 80, abs=0.1)
    assert card.loc["Bolt Electric", "note"] == "low volume"
    assert list(card.index) == ["Acme HVAC", "Bolt Electric"]


def test_open_jobs_ignored_in_rates(tmp_path):
    df = jobs(tmp_path, (
        "1,Acme HVAC,2026-03-01,2026-03-01,no,100,100\n"
        "2,Acme HVAC,2026-03-02,,,100,\n"
    ))
    row = build_scorecard(df, min_jobs=1).iloc[0]
    assert row["jobs"] == 2 and row["completed"] == 1 and row["on_time_pct"] == 100.0


def test_vendor_with_no_completed_jobs(tmp_path):
    df = jobs(tmp_path, "1,Ghost Co,2026-03-01,,,100,\n")
    row = build_scorecard(df).iloc[0]
    assert row["score"] == 0.0 and row["note"] == "no completed jobs"


def test_custom_weights(tmp_path):
    df = jobs(tmp_path, "1,Acme HVAC,2026-03-01,2026-03-09,no,100,100\n")
    heavy_cost = build_scorecard(df, {"on_time": 0.0, "reopen": 0.0, "cost": 1.0}).iloc[0]["score"]
    assert heavy_cost == 100.0


def test_weights_must_sum_to_one(tmp_path):
    df = jobs(tmp_path, "1,Acme HVAC,2026-03-01,2026-03-01,no,100,100\n")
    with pytest.raises(ValueError, match="add up to 1"):
        build_scorecard(df, {"on_time": 0.5, "reopen": 0.5, "cost": 0.5})
    with pytest.raises(ValueError):
        build_scorecard(df, {"on_time": 1.0})


def test_load_errors(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("wo_id,vendor\n1,A\n")
    with pytest.raises(ValueError, match="missing columns"):
        load_jobs(path)
    with pytest.raises(ValueError, match="bad date"):
        jobs(tmp_path, "1,A,03/01/2026,,,1,1\n")
    with pytest.raises(ValueError, match="bad number"):
        jobs(tmp_path, "1,A,2026-03-01,2026-03-01,no,abc,1\n")


def test_zero_estimate_does_not_divide(tmp_path):
    df = jobs(tmp_path, "1,A,2026-03-01,2026-03-01,no,0,0\n")
    assert build_scorecard(df).iloc[0]["cost_var_pct"] == 0.0


def test_cli_sample_and_errors(capsys, tmp_path):
    assert main([str(SAMPLE)]) == 0
    assert "Acme HVAC" in capsys.readouterr().out
    assert main([str(tmp_path / "none.csv")]) == 1
    assert main([str(SAMPLE), "--weights", "0.9,0.9,0.9"]) == 1
