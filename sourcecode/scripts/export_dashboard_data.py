"""
export_dashboard_data.py - prepare the files Power BI / Tableau loads (writes to dashboard/data/).

Copies the cleaned tables the dashboard needs and builds four derived tables that are awkward to make in a BI tool:
  nav_vs_benchmark.csv      NAV and the fund's benchmark, both rebased to 100 (Page 2 line chart)
  sip_vs_nifty_monthly.csv  monthly SIP inflow with the month-end Nifty 50 (Page 4 dual-axis chart)
  transactions_enriched.csv transactions joined to fund details with a month column (Page 3)
  fund_scorecard.csv        composite scorecard from compute_metrics.py (Page 2 table)
"""
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
OUT = ROOT / "dashboard" / "data"
BM_MAP = {"NIFTY 50 TRI": "NIFTY50", "NIFTY 100 TRI": "NIFTY100", "NIFTY 500 TRI": "NIFTY500", "NIFTY Midcap 150 TRI": "NIFTY_MIDCAP150",
          "NIFTY Midcap 50 TRI": "NIFTY_MIDCAP150", "NIFTY Large Midcap 250 TRI": "NIFTY500", "BSE 250 SmallCap TRI": "BSE_SMALLCAP",
          "CRISIL Liquid Fund AI Index": "CRISIL_LIQUID", "CRISIL Dynamic Gilt Index": "CRISIL_GILT", "CRISIL Short Term Bond Index": "CRISIL_LIQUID"}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ["fund_master", "aum_by_fund_house", "monthly_sip_inflows", "category_inflows", "industry_folio_count",
                 "scheme_performance", "portfolio_holdings", "benchmark_indices"]:
        shutil.copy(PROC / f"{name}_clean.csv", OUT / f"{name}.csv")
    shutil.copy(PROC / "fund_scorecard.csv", OUT / "fund_scorecard.csv")

    fm = pd.read_csv(PROC / "fund_master_clean.csv")
    nav = pd.read_csv(PROC / "nav_history_clean.csv", parse_dates=["date"])
    nav = nav[nav["is_filled"] == 0] if "is_filled" in nav.columns else nav
    bm = pd.read_csv(PROC / "benchmark_indices_clean.csv", parse_dates=["date"])
    sip = pd.read_csv(PROC / "monthly_sip_inflows_clean.csv", parse_dates=["month"])
    tx = pd.read_csv(PROC / "investor_transactions_clean.csv", parse_dates=["transaction_date"])

    # NAV vs benchmark, both rebased to 100 at each fund's first date
    f = fm[["amfi_code", "scheme_name", "benchmark"]].assign(benchmark_index=lambda d: d["benchmark"].map(BM_MAP))
    d = nav[["amfi_code", "date", "nav"]].merge(f, on="amfi_code").merge(
        bm.rename(columns={"index_name": "benchmark_index", "close_value": "benchmark_close"}), on=["benchmark_index", "date"], how="left")
    d = d.sort_values(["amfi_code", "date"])
    d["nav_rebased"] = d["nav"] / d.groupby("amfi_code")["nav"].transform("first") * 100
    d["benchmark_rebased"] = d["benchmark_close"] / d.groupby("amfi_code")["benchmark_close"].transform("first") * 100
    d.drop(columns=["benchmark_close"]).round(4).to_csv(OUT / "nav_vs_benchmark.csv", index=False)

    # SIP inflow with month-end Nifty 50
    n50 = bm[bm["index_name"] == "NIFTY50"].set_index("date")["close_value"].resample("MS").last().rename("nifty50_month_end").reset_index().rename(columns={"date": "month"})
    sip.merge(n50, on="month", how="left")[["month", "sip_inflow_crore", "active_sip_accounts_crore", "new_sip_accounts_lakh", "yoy_growth_pct", "nifty50_month_end"]].to_csv(OUT / "sip_vs_nifty_monthly.csv", index=False)

    # Transactions enriched with fund details
    keep = ["investor_id", "transaction_date", "amfi_code", "transaction_type", "amount_inr", "state", "city", "city_tier", "age_group",
            "gender", "annual_income_lakh", "payment_mode", "kyc_status"]
    e = tx[keep].merge(fm[["amfi_code", "scheme_name", "fund_house", "category", "sub_category", "plan"]], on="amfi_code", how="left")
    e["month"] = e["transaction_date"].dt.to_period("M").dt.to_timestamp()
    e["signed_amount_inr"] = e["amount_inr"].where(e["transaction_type"] != "Redemption", -e["amount_inr"])
    e.to_csv(OUT / "transactions_enriched.csv", index=False)

    for f_ in sorted(OUT.glob("*.csv")):
        print(f"  {f_.name:<28} {sum(1 for _ in open(f_, encoding='utf-8')) - 1:>7,} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
