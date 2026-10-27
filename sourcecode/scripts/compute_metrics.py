"""
compute_metrics.py - performance and risk metrics from NAV history (Day 4 + Day 6 formulas).

All formulas follow the project brief:
  * Trading-day basis: 252 days a year (never calendar days). Real reported NAVs only (is_filled = 0).
  * Annualised return = (1 + daily_return).prod() ** (252 / n) - 1
  * CAGR            = (NAV_end / NAV_start) ** (1 / years) - 1, with years = trading_days / 252
  * Sharpe          = (Rp - Rf) / Std(Rp), annualised with sqrt(252), Rf = 6.5%
  * Sortino         = (Rp - Rf) / Downside_Std, Downside_Std from negative-return days only
  * Alpha, Beta     = OLS of fund returns on Nifty 100 returns; alpha = intercept * 252, beta = slope
  * Max drawdown    = min(NAV / running_max - 1)
  * VaR / CVaR (95%) = 5th percentile of daily returns / mean of returns at or below it

Usage:  python scripts/compute_metrics.py     (writes the CSVs listed in main() to data/processed/)
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
RF, TD, CONF = 0.065, 252, 0.95
BENCH_ALPHA_BETA = "NIFTY100"          # index used for alpha / beta, as in the brief
WEIGHTS = {"cagr_3yr": 0.30, "sharpe": 0.25, "alpha": 0.20, "expense_ratio_pct": 0.15, "max_drawdown": 0.10}
INVERSE = {"expense_ratio_pct"}        # lower is better; for max_drawdown a smaller (less negative) fall is better


def read(name, dates=()):
    df = pd.read_csv(PROC / f"{name}_clean.csv")
    for c in dates:
        df[c] = pd.to_datetime(df[c])
    return df


def load_inputs(proc=None):
    global PROC
    if proc is not None:
        PROC = Path(proc)
    fm = read("fund_master", ["launch_date"])
    nav = read("nav_history", ["date"])
    bm = read("benchmark_indices", ["date"])
    nav = nav[nav["is_filled"] == 0] if "is_filled" in nav.columns else nav   # real NAVs only
    nav_p = nav.pivot(index="date", columns="amfi_code", values="nav").sort_index()
    bm_p = bm.pivot(index="date", columns="index_name", values="close_value").sort_index()
    return fm, nav_p, bm_p


# ----------------------------------------------------------------------------- formulas
def annualised_return(r):
    r = r.dropna()
    return (1 + r).prod() ** (TD / len(r)) - 1


def cagr(nav_s, years):
    """CAGR over the last `years` years of trading days (NaN if the history is too short)."""
    nav_s = nav_s.dropna()
    n = int(round(TD * years))
    if len(nav_s) <= n:
        return np.nan
    return (nav_s.iloc[-1] / nav_s.iloc[-1 - n]) ** (1 / years) - 1


def cagr_since_start(nav_s):
    nav_s = nav_s.dropna()
    years = (len(nav_s) - 1) / TD
    return (nav_s.iloc[-1] / nav_s.iloc[0]) ** (1 / years) - 1


def sharpe(r, rf=RF):
    r = r.dropna()
    return (r.mean() - rf / TD) / r.std() * np.sqrt(TD)


def sortino(r, rf=RF):
    r = r.dropna()
    downside_std = r[r < 0].std() * np.sqrt(TD)
    return (r.mean() * TD - rf) / downside_std


def alpha_beta(r_fund, r_bench):
    d = pd.concat([r_fund, r_bench], axis=1, keys=["f", "b"]).dropna()
    res = stats.linregress(d["b"], d["f"])
    te = (d["f"] - d["b"]).std() * np.sqrt(TD)
    return {"alpha": res.intercept * TD, "beta": res.slope, "r_squared": res.rvalue ** 2, "p_value": res.pvalue,
            "tracking_error": te, "information_ratio": (d["f"].mean() - d["b"].mean()) * TD / te if te else np.nan}


def max_drawdown(nav_s):
    nav_s = nav_s.dropna()
    dd = nav_s / nav_s.cummax() - 1
    trough = dd.idxmin()
    peak = nav_s.loc[:trough].idxmax()
    after = nav_s.loc[trough:]
    rec = after[after >= nav_s.loc[peak]]
    return {"max_drawdown": dd.min(), "peak_date": peak, "trough_date": trough,
            "recovery_date": rec.index[0] if len(rec) else pd.NaT,
            "days_to_recover": (rec.index[0] - trough).days if len(rec) else np.nan}


def var_cvar(r, conf=CONF):
    r = r.dropna()
    var = np.percentile(r, (1 - conf) * 100)
    return {"var_95": var, "cvar_95": r[r <= var].mean()}


# ----------------------------------------------------------------------------- scorecard
def scorecard(df, weights=WEIGHTS, within=None):
    """Composite 0-100 score from percentile ranks. within='category' ranks funds only against their asset class."""
    total = pd.Series(0.0, index=df.index)
    for col, w in weights.items():
        vals = -df[col] if col in INVERSE else df[col]
        ranks = vals.groupby(df[within]).rank(pct=True) if within else vals.rank(pct=True)
        total += w * ranks
    return total / sum(weights.values()) * 100


# ----------------------------------------------------------------------------- all funds
def compute_all():
    fm, nav_p, bm_p = load_inputs()
    ret, bm_ret = nav_p.pct_change().dropna(how="all"), bm_p.pct_change().dropna(how="all")
    info = fm.set_index("amfi_code")
    base = lambda c: {"amfi_code": c, "scheme_name": info.loc[c, "scheme_name"]}
    rows = {k: [] for k in ["returns", "cagr", "sharpe", "sortino", "ab", "dd", "var"]}
    for c in nav_p.columns:
        r, s = ret[c].dropna(), nav_p[c].dropna()
        rows["returns"].append({**base(c), "trading_days": len(r), "mean_daily_return_pct": r.mean() * 100,
                                "daily_std_pct": r.std() * 100, "annualised_return": annualised_return(r),
                                "annualised_volatility": r.std() * np.sqrt(TD)})
        rows["cagr"].append({**base(c), "cagr_1yr": cagr(s, 1), "cagr_3yr": cagr(s, 3), "cagr_5yr": cagr(s, 5),
                             "cagr_since_start": cagr_since_start(s), "years_of_history": (len(s) - 1) / TD})
        rows["sharpe"].append({**base(c), "annualised_return": r.mean() * TD, "annualised_volatility": r.std() * np.sqrt(TD),
                               "risk_free_rate": RF, "sharpe": sharpe(r)})
        rows["sortino"].append({**base(c), "annualised_return": r.mean() * TD, "downside_std": r[r < 0].std() * np.sqrt(TD),
                                "risk_free_rate": RF, "sortino": sortino(r)})
        rows["ab"].append({**base(c), "benchmark": BENCH_ALPHA_BETA, **alpha_beta(r, bm_ret[BENCH_ALPHA_BETA])})
        rows["dd"].append({**base(c), **max_drawdown(s)})
        rows["var"].append({**base(c), **var_cvar(r), "var_inr_per_lakh": -var_cvar(r)["var_95"] * 100000,
                            "cvar_inr_per_lakh": -var_cvar(r)["cvar_95"] * 100000})
    out = {k: pd.DataFrame(v) for k, v in rows.items()}

    sc = fm[["amfi_code", "scheme_name", "fund_house", "category", "sub_category", "plan", "risk_category", "expense_ratio_pct"]]
    for key, cols in [("cagr", ["cagr_1yr", "cagr_3yr", "cagr_since_start"]), ("sharpe", ["sharpe"]), ("sortino", ["sortino"]),
                      ("ab", ["alpha", "beta", "r_squared"]), ("dd", ["max_drawdown"])]:
        sc = sc.merge(out[key][["amfi_code"] + cols], on="amfi_code")
    sc["score"] = scorecard(sc).round(1)
    sc["rank_overall"] = sc["score"].rank(ascending=False, method="min").astype(int)
    sc["score_in_class"] = scorecard(sc, within="category").round(1)
    sc["rank_in_class"] = sc.groupby("category")["score_in_class"].rank(ascending=False, method="min").astype(int)
    sc["tier"] = pd.qcut(sc["score"], 4, labels=["Bottom quartile", "Below average", "Above average", "Top quartile"])
    out["scorecard"] = sc.sort_values("rank_overall")
    return out, (fm, nav_p, bm_p, ret, bm_ret)


FILES = {"returns": "returns_computed", "cagr": "cagr_report", "sharpe": "sharpe_values", "sortino": "sortino_values",
         "ab": "alpha_beta", "dd": "max_drawdown", "var": "var_cvar_report", "scorecard": "fund_scorecard"}


def main():
    out, _ = compute_all()
    for key, fname in FILES.items():
        out[key].to_csv(PROC / f"{fname}.csv", index=False)
        print(f"  {fname + '.csv':<24} {len(out[key]):>4} rows")
    print("\nTop 5 by composite score:")
    print(out["scorecard"][["rank_overall", "scheme_name", "score", "cagr_3yr", "sharpe", "alpha"]].head().round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
