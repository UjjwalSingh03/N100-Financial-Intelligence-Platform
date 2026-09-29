-- Day 14 demo: latest-year five-company KPI preview
WITH latest AS (
  SELECT company_id, MAX(year) AS year FROM financial_ratios GROUP BY company_id
)
SELECT r.company_id,r.year,r.net_profit_margin_pct,r.operating_profit_margin_pct,
r.return_on_equity_pct,r.debt_to_equity,r.interest_coverage,r.asset_turnover,
r.free_cash_flow_cr,r.capex_cr,r.earnings_per_share,r.book_value_per_share,
r.dividend_payout_ratio_pct,r.total_debt_cr,r.cash_from_operations_cr,
r.revenue_cagr_5yr,r.pat_cagr_5yr,r.eps_cagr_5yr,r.composite_quality_score
FROM financial_ratios r JOIN latest l ON l.company_id=r.company_id AND l.year=r.year
ORDER BY r.company_id LIMIT 5;
