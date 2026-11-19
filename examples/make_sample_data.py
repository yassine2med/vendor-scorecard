"""Generate synthetic vendor jobs. Run: python examples/make_sample_data.py"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(7)
# name: (trade, chance late, chance reopened, cost bias, job count)
VENDORS = {
    "Acme HVAC": ("HVAC", 0.10, 0.04, 1.00, 45),
    "Northside Plumbing": ("Plumbing", 0.25, 0.12, 1.08, 40),
    "Brightline Electric": ("Electrical", 0.05, 0.03, 0.97, 38),
    "Oak and Pine Carpentry": ("Carpentry", 0.40, 0.20, 1.20, 30),
    "CleanSweep Services": ("Custodial", 0.15, 0.05, 1.02, 35),
    "Pilot Roofing": ("Roofing", 0.20, 0.10, 1.05, 4),
}

rows = []
n = 0
for vendor, (trade, late_p, reopen_p, bias, count) in VENDORS.items():
    for _ in range(count):
        n += 1
        due = date(2026, 1, 5) + timedelta(days=random.randint(0, 270))
        estimate = round(random.uniform(150, 2500), 2)
        open_job = random.random() < 0.05
        if open_job:
            completed, reopened, actual = "", "", ""
        else:
            late = random.random() < late_p
            completed = due + timedelta(days=random.randint(1, 9) if late else -random.randint(0, 4))
            reopened = "yes" if random.random() < reopen_p else "no"
            actual = round(estimate * bias * random.uniform(0.9, 1.1), 2)
            completed = completed.isoformat()
        rows.append({"wo_id": f"WO-{4000 + n}", "vendor": vendor, "trade": trade, "due_date": due.isoformat(),
                     "completed_date": completed, "reopened": reopened, "estimate": estimate, "actual_cost": actual})

out = Path(__file__).resolve().parent.parent / "data" / "vendor_jobs.csv"
with out.open("w", newline="") as fh:
    writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
print(f"wrote {len(rows)} rows to {out}")
