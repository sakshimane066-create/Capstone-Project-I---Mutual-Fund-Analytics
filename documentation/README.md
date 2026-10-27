# Bluestock Fintech: Mutual Fund Analytics Capstone

End-to-end data project for 40 mutual fund schemes: ETL pipeline, SQLite star schema, EDA, performance and risk analytics, and a Power BI dashboard.
**Author:** Sakshi Mane. For educational purposes only; not investment advice.

## Quick start
```
pip install -r requirements.txt
# 1. put the 10 source CSVs in data/raw/
python run_pipeline.py          # ETL -> metrics -> dashboard data -> SQL queries -> data dictionary
# 2. run the notebooks in order (Kernel > Restart & Run All)
cd notebooks && jupyter notebook
```

## What each part does
| Path | Purpose |
|---|---|
| `run_pipeline.py` | Master script: runs every step below with one command |
| `scripts/etl_pipeline.py` | ETL: checks sources, cleans (`clean_data.py`), loads SQLite (`load_db.py`), verifies row counts and foreign keys; logs to `logs/etl.log` |
| `scripts/compute_metrics.py` | Returns, CAGR, Sharpe, Sortino, alpha/beta, max drawdown, VaR/CVaR and the fund scorecard |
| `scripts/recommender.py` | Top 3 funds by Sharpe for a Low / Moderate / High risk appetite |
| `scripts/export_dashboard_data.py` | Builds the files Power BI loads into `dashboard/data/` |
| `sql/schema.sql`, `sql/queries.sql` | 8-table star schema (plus 3 supporting tables) and 10 analytical queries; results in `sql/query_results.md` |
| `data/db/bluestock_mf.db` | The SQLite database |
| `data/processed/` | 10 cleaned CSVs plus every computed metric file |
| `data_dictionary.md` | Every column, type and business definition |
| `dashboard/` | `DASHBOARD_GUIDE.md` (step-by-step Power BI build), `bluestock_theme.json`, `data/` |
| `reports/` | Charts in `figures/`; `Final_Report.pdf` and `Presentation.pptx` |

## Notebooks (run in this order)
| # | Notebook | Day | Main outputs |
|---|---|---|---|
| 1 | `01_data_ingestion.ipynb` | 1 | Shapes, dtypes, AMFI code validation |
| 2 | `02_data_cleaning.ipynb` | Week 1 | Cleaned datasets, KPIs, regression |
| 3 | `03_eda_analysis.ipynb` | 3 | 25 charts and 10 findings |
| 4 | `04_performance_analytics.ipynb` | 4 | `returns_computed`, `cagr_report`, `sharpe_values`, `sortino_values`, `alpha_beta`, `max_drawdown`, `fund_scorecard`, `benchmark_chart.png` |
| 5 | `05_advanced_analytics.ipynb` | 6 | `var_cvar_report`, `rolling_sharpe_chart.png`, `cohort_analysis`, `sip_continuity`, `sector_hhi` |

## Methods and assumptions
- 252 trading days a year; only real reported NAVs are used for returns (weekend rows added by forward-fill are flagged `is_filled = 1` and excluded).
- Risk-free rate 6.5%. Sharpe uses daily excess returns annualised with sqrt(252). Sortino uses the standard deviation of negative-return days.
- Alpha and beta come from an OLS regression of fund returns on Nifty 100 returns (alpha = intercept x 252).
- Scorecard weights: 30% 3-year CAGR, 25% Sharpe, 20% alpha, 15% expense ratio (inverse), 10% max drawdown (inverse), on percentile ranks.

## Data findings to be aware of
- NAV history is about 4.6 years, so a 5-year CAGR cannot be computed; "since start" is reported instead.
- Fund NAVs barely move with the benchmark indices (average R-squared about 0.001), so OLS alpha and beta are not meaningful here.
- The provider's reported Sharpe, drawdown and 3-year return do not match values calculated from NAV (volatility matches exactly).
- Investors have only about 6.6 transactions each over 17 months, so the 35-day SIP-gap rule flags almost everyone; a relative flag is provided too.
- Transaction data is synthetic. AUM covers the 10 largest fund houses only.
