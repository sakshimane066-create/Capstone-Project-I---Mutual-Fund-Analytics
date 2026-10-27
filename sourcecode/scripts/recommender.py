"""
recommender.py - simple fund recommendation by investor risk appetite (Day 6).

Rule: map the investor's appetite (Low / Moderate / High) to the matching SEBI risk categories, then return the
top N funds by Sharpe ratio inside that group.

    Low      -> Low
    Moderate -> Moderate, Moderately High
    High     -> High, Very High

Usage:
    python scripts/recommender.py High
    python scripts/recommender.py Moderate --top 5 --plan Direct
or from Python:   from recommender import recommend;  recommend("Low")
"""
import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
APPETITE_TO_RISK = {"low": ["Low"], "moderate": ["Moderate", "Moderately High"], "high": ["High", "Very High"]}


def recommend(appetite, top_n=3, plan=None, proc=PROC):
    """Return the top_n funds by Sharpe ratio for the given risk appetite (optionally only 'Direct' or 'Regular')."""
    key = str(appetite).strip().lower()
    if key not in APPETITE_TO_RISK:
        raise ValueError(f"risk appetite must be one of Low, Moderate, High (got {appetite!r})")
    funds = pd.read_csv(Path(proc) / "fund_scorecard.csv")
    pool = funds[funds["risk_category"].isin(APPETITE_TO_RISK[key])]
    if plan:
        pool = pool[pool["plan"].str.lower() == plan.lower()]
    cols = ["scheme_name", "fund_house", "sub_category", "plan", "risk_category", "sharpe", "cagr_3yr", "max_drawdown", "expense_ratio_pct"]
    return pool.nlargest(top_n, "sharpe")[cols].reset_index(drop=True).rename_axis("rank").reset_index().assign(rank=lambda d: d["rank"] + 1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("appetite", help="Low, Moderate or High")
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--plan", choices=["Direct", "Regular"])
    a = ap.parse_args()
    out = recommend(a.appetite, a.top, a.plan)
    print(f"\nTop {a.top} funds for a {a.appetite} risk appetite (ranked by Sharpe ratio):\n")
    print(out.round(3).to_string(index=False))
