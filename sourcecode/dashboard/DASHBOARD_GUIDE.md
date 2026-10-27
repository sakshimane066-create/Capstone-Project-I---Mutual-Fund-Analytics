# Power BI Dashboard Build Guide (Day 5)

Deliverables: `bluestock_mf_dashboard.pbix`, `Dashboard.pdf`, 4 page screenshots (save them in `dashboard/`).
Time: about 5-6 hours. Everything below uses the files in `dashboard/data/` (created by `python run_pipeline.py`).

## 1. Load the data (45 min)
1. **Load all 12 tables at once from one workbook** (Text/CSV loads only one file at a time):
   Power BI Desktop > **Get data > Excel workbook** > choose `dashboard/data/bluestock_dashboard_data.xlsx`.
   In the Navigator window tick **Select multiple items**, tick all 12 sheets, then click **Transform Data** (not Load) so you can check the types in step 2.
   Sheets: `fund_master`, `fund_scorecard`, `scheme_performance`, `nav_vs_benchmark`, `transactions_enriched`, `aum_by_fund_house`,
   `monthly_sip_inflows`, `sip_vs_nifty_monthly`, `category_inflows`, `industry_folio_count`, `portfolio_holdings`, `benchmark_indices`.
   (Do not use the old `*_clean.xls` files: they are CSV text saved with an .xls name and Power BI rejects them. If you ever need the CSVs, use Get data > Text/CSV one file at a time.)
2. In **Transform data**, check the types: date columns (`date`, `month`, `transaction_date`, `launch_date`, `portfolio_date`) should show the Date icon, and `amfi_code` should be **Text** in every table (the workbook already stores them that way). Then click **Close & Apply**.
3. **Calendar table** (Modeling > New table):
   ```
   Calendar = ADDCOLUMNS(CALENDAR(DATE(2022,1,1), DATE(2026,5,31)), "Year", YEAR([Date]), "Month No", MONTH([Date]), "YearMonth", YEAR([Date]) * 100 + MONTH([Date]), "Month", FORMAT([Date], "MMM yyyy"))
   ```
   Then select the `Month` column > Column tools > **Sort by column > YearMonth**.
   ```
   ```
4. **Relationships** (Model view, one-to-many, single direction from the 1 side):
   | From (1 side) | To (many side) |
   |---|---|
   | `fund_master[amfi_code]` | `fund_scorecard`, `scheme_performance`, `nav_vs_benchmark`, `transactions_enriched`, `portfolio_holdings` (each `[amfi_code]`) |
   | `Calendar[Date]` | `aum_by_fund_house[date]`, `monthly_sip_inflows[month]`, `sip_vs_nifty_monthly[month]`, `category_inflows[month]`, `transactions_enriched[transaction_date]`, `nav_vs_benchmark[date]` |
   Check that all tables loaded (the brief says to verify 8+ tables).
5. **Theme:** View > Themes > Browse for themes > `bluestock_theme.json`.

## 2. Measures (paste into a new table named `Measures`)
```
Latest AUM (lakh crore) = CALCULATE(SUM(aum_by_fund_house[aum_lakh_crore]), aum_by_fund_house[date] = MAX(aum_by_fund_house[date]))
Latest SIP Inflow (crore) = CALCULATE(SUM(monthly_sip_inflows[sip_inflow_crore]), monthly_sip_inflows[month] = MAX(monthly_sip_inflows[month]))
Latest Folios (crore) = CALCULATE(SUM(industry_folio_count[total_folios_crore]), industry_folio_count[month] = MAX(industry_folio_count[month]))
Schemes (10 AMCs) = CALCULATE(SUM(aum_by_fund_house[num_schemes]), aum_by_fund_house[date] = MAX(aum_by_fund_house[date]))
Total Invested (crore) = DIVIDE(CALCULATE(SUM(transactions_enriched[amount_inr]), transactions_enriched[transaction_type] <> "Redemption"), 10000000)
Net Flow (crore) = DIVIDE(SUM(transactions_enriched[signed_amount_inr]), 10000000)
Avg SIP Amount = CALCULATE(AVERAGE(transactions_enriched[amount_inr]), transactions_enriched[transaction_type] = "SIP")
Top Performer = MAXX(TOPN(1, fund_scorecard, fund_scorecard[score]), fund_scorecard[scheme_name])
SIP Accounts YoY % =
VAR latest = MAX(monthly_sip_inflows[month])
VAR cur = CALCULATE(SUM(monthly_sip_inflows[active_sip_accounts_crore]), monthly_sip_inflows[month] = latest)
VAR prev = CALCULATE(SUM(monthly_sip_inflows[active_sip_accounts_crore]), monthly_sip_inflows[month] = EDATE(latest, -12))
RETURN DIVIDE(cur - prev, prev)
```
Note: the AUM table covers the 10 largest fund houses (about Rs 62.7 lakh crore at Dec 2025). The brief's industry figures (Rs 81 lakh crore AUM, 1,908 schemes) are not in the data, so show them as text cards labelled "AMFI, Dec 2025" and label the data-driven card "Top-10 AMC AUM".

## 3. Pages (every page needs at least 2 slicers)
**Page 1: Industry Overview**
- KPI cards (4): Top-10 AMC AUM = `Latest AUM`, SIP inflow = `Latest SIP Inflow`, Folios = `Latest Folios`, Schemes = `Schemes (10 AMCs)`.
- Line chart: X `aum_by_fund_house[date]`, Y `sum of aum_lakh_crore`, Legend off (total). Title "AUM, top 10 fund houses".
- Bar chart: Y `fund_house`, X `Latest AUM`. Sort descending.
- Slicers: `fund_house`, `Calendar[Year]`.

**Page 2: Fund Performance**
- Scatter: X `scheme_performance[return_3yr_pct]`, Y `scheme_performance[std_dev_ann_pct]`, Size `aum_crore`, Legend `fund_master[category]`, Details `fund_master[scheme_name]`.
- Table: from `fund_scorecard`: `rank_overall`, `scheme_name`, `score`, `cagr_3yr`, `sharpe`, `alpha`, `max_drawdown`, `tier`. Add conditional formatting (data bars on `score`, colour scale on `sharpe`). Sortable by clicking headers.
- Line chart: X `nav_vs_benchmark[date]`, Y `nav_rebased` and `benchmark_rebased` (Average). It follows the fund selected in the table.
- Slicers: `fund_master[fund_house]`, `fund_master[category]`, `fund_master[plan]`.
- **Drill-through:** create a page "Fund Detail" with the NAV line chart and key KPIs; drag `fund_master[scheme_name]` into its **Drill-through** well. Right-click a fund in the table > Drill through > Fund Detail.
- **Tooltip page:** add a page, set Page information > Allow use as tooltip, put `sharpe`, `max_drawdown`, `cagr_3yr` cards on it, then set it as the scatter's tooltip.

**Page 3: Investor Analytics**
- Filled map (or bar chart) by `transactions_enriched[state]`, value `Total Invested (crore)`. If the map cannot place states, use a horizontal bar chart (12 states).
- Donut: Legend `transaction_type`, Values `sum of amount_inr`.
- Bar chart: X `age_group`, Y `Avg SIP Amount`.
- Line chart: X `transactions_enriched[month]`, Y `Total Invested (crore)` and `Net Flow (crore)`.
- Slicers: `state`, `age_group`, `city_tier`.

**Page 4: SIP and Market Trends**
- Combo chart (line and clustered column): X `sip_vs_nifty_monthly[month]`, Column `sip_inflow_crore`, Line (secondary axis) `nifty50_month_end`.
- Matrix heatmap: Rows `category_inflows[category]`, Columns `month`, Values `sum of net_inflow_crore`; Format > Cell elements > Background colour scale (red to green, centre 0).
- Bar chart: top 5 categories by net inflow (Visual filter > Top N = 5 by `sum of net_inflow_crore`). The data covers FY 2024-25 (Apr 2024 to Mar 2025).
- KPI card: `SIP Accounts YoY %`.
- Slicers: `Calendar[Year]`, `category_inflows[category]`.

## 4. Polish (30 min)
Add the Bluestock logo (Insert > Image) to each page, use the same title style, align visuals to a grid, turn off unused axis titles, add alt text.

## 5. Export (20 min)
- **PDF:** File > Export > Export to PDF > save as `dashboard/Dashboard.pdf`.
- **Page screenshots:** open each page, press `Win + Shift + S`, save as `page1_industry.png`, `page2_performance.png`, `page3_investor.png`, `page4_sip_market.png`.
- **Publish (optional, 30 min):** Home > Publish to Power BI Service (needs a work or school account) or use Tableau Public, then add the public URL to the README.

## 6. Check before submitting
- [ ] 4 pages, each with 2+ slicers
- [ ] KPI cards show the right numbers (Top-10 AMC AUM about 62.7 lakh crore, SIP inflow 31,002 crore, folios 26.12 crore)
- [ ] Drill-through and tooltips work
- [ ] `.pbix`, `Dashboard.pdf` and 4 PNGs saved in `dashboard/`
