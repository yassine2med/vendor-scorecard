"""Vendor scorecard: on-time rate, reopen rate and cost variance from job rows."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED = ("wo_id", "vendor", "due_date", "completed_date", "reopened", "estimate", "actual_cost")
DEFAULT_WEIGHTS = {"on_time": 0.5, "reopen": 0.3, "cost": 0.2}
REOPEN_CAP = 0.20  # a reopen rate at or above this scores 0
COST_CAP = 0.25  # cost over estimate by this share or more scores 0
GRADES = [(90, "A"), (80, "B"), (70, "C"), (60, "D")]


def load_jobs(path: str | Path) -> pd.DataFrame:
    """Read the job CSV. Raises ValueError for missing columns, bad dates or bad numbers."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"missing columns: {', '.join(missing)}")
    for col in ("due_date", "completed_date"):
        parsed = pd.to_datetime(df[col].replace("", pd.NA), format="%Y-%m-%d", errors="coerce")
        if (df[col].ne("") & parsed.isna()).any():
            raise ValueError(f"bad date in column '{col}'")
        df[col] = parsed
    if df["due_date"].isna().any():
        raise ValueError("every job needs a due_date")
    for col in ("estimate", "actual_cost"):
        numbers = pd.to_numeric(df[col].replace("", pd.NA), errors="coerce")
        if (df[col].ne("") & numbers.isna()).any():
            raise ValueError(f"bad number in column '{col}'")
        df[col] = numbers
    df["reopened"] = df["reopened"].str.strip().str.lower().map({"yes": True, "no": False})
    return df


def grade(score: float) -> str:
    """Letter grade for a 0-100 score."""
    for floor, letter in GRADES:
        if score >= floor:
            return letter
    return "F"


def component_scores(on_time: float, reopen_rate: float, cost_variance: float) -> dict[str, float]:
    """Turn the three raw rates into 0-100 component scores.

    on_time and reopen_rate are fractions. cost_variance is (actual - estimate) / estimate.
    """
    return {
        "on_time": 100 * min(max(on_time, 0.0), 1.0),
        "reopen": 100 * (1 - min(max(reopen_rate, 0.0) / REOPEN_CAP, 1.0)),
        "cost": 100 * (1 - min(max(cost_variance, 0.0) / COST_CAP, 1.0)),
    }


def build_scorecard(df: pd.DataFrame, weights: dict[str, float] | None = None, min_jobs: int = 10) -> pd.DataFrame:
    """One row per vendor, best score first. Vendors with a note (low volume) are listed last.

    Only completed jobs count toward the rates. Vendors with fewer completed jobs than
    min_jobs get the note 'low volume'.
    """
    weights = weights or DEFAULT_WEIGHTS
    if set(weights) != set(DEFAULT_WEIGHTS) or abs(sum(weights.values()) - 1) > 1e-9:
        raise ValueError("weights need on_time, reopen and cost, and must add up to 1")
    rows = []
    for vendor, jobs in df.groupby("vendor"):
        done = jobs[jobs["completed_date"].notna()]
        if done.empty:
            rows.append({"vendor": vendor, "jobs": len(jobs), "completed": 0, "score": 0.0, "grade": "F", "note": "no completed jobs"})
            continue
        on_time = float((done["completed_date"] <= done["due_date"]).mean())
        reopen_rate = float(done["reopened"].fillna(False).astype(bool).mean())
        estimate = float(done["estimate"].sum())
        variance = (float(done["actual_cost"].sum()) - estimate) / estimate if estimate else 0.0
        parts = component_scores(on_time, reopen_rate, variance)
        score = round(sum(parts[k] * weights[k] for k in weights), 1)
        rows.append({
            "vendor": vendor, "jobs": len(jobs), "completed": len(done),
            "on_time_pct": round(on_time * 100, 1), "reopen_pct": round(reopen_rate * 100, 1),
            "cost_var_pct": round(variance * 100, 1), "score": score, "grade": grade(score),
            "note": "low volume" if len(done) < min_jobs else "",
        })
    out = pd.DataFrame(rows)
    out["_thin"] = out["note"].ne("")
    out = out.sort_values(["_thin", "score"], ascending=[True, False], ignore_index=True).drop(columns="_thin")
    return out.fillna({"on_time_pct": 0.0, "reopen_pct": 0.0, "cost_var_pct": 0.0})
