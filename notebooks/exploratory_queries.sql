-- Sprint 1 Day 07: Exploratory SQL
-- Run against the regenerated nifty100.db.
-- The queries are read-only and use the current schema names.

-- Q01. Company universe size
SELECT COUNT(*) AS company_count
FROM companies;

-- Q02. Row counts across all populated tables
SELECT 'companies' AS table_name, COUNT(*) AS row_count FROM companies
UNION ALL SELECT 'profitandloss', COUNT(*) FROM profitandloss
UNION ALL SELECT 'balancesheet', COUNT(*) FROM balancesheet
UNION ALL SELECT 'cashflow', COUNT(*) FROM cashflow
UNION ALL SELECT 'analysis', COUNT(*) FROM analysis
UNION ALL SELECT 'documents', COUNT(*) FROM documents
UNION ALL SELECT 'prosandcons', COUNT(*) FROM prosandcons
UNION ALL SELECT 'sectors', COUNT(*) FROM sectors
UNION ALL SELECT 'stock_prices', COUNT(*) FROM stock_prices
UNION ALL SELECT 'financial_ratios', COUNT(*) FROM financial_ratios
UNION ALL SELECT 'market_cap', COUNT(*) FROM market_cap
UNION ALL SELECT 'peer_groups', COUNT(*) FROM peer_groups;

-- Q03. Latest available P&L records by net profit
SELECT c.id AS company_id,
       c.company_name,
       p.year,
       p.sales,
       p.operating_profit,
       p.net_profit,
       p.eps
FROM profitandloss p
JOIN companies c ON c.id = p.company_id
WHERE p.year = (SELECT MAX(year) FROM profitandloss)
ORDER BY p.net_profit DESC
LIMIT 10;

-- Q04. Latest available P&L records by sales
SELECT c.id AS company_id,
       c.company_name,
       p.year,
       p.sales,
       p.opm_percentage,
       p.net_profit
FROM profitandloss p
JOIN companies c ON c.id = p.company_id
WHERE p.year = (SELECT MAX(year) FROM profitandloss)
ORDER BY p.sales DESC
LIMIT 10;

-- Q05. Average operating margin by sector using the latest P&L year
SELECT c.sector,
       p.year,
       ROUND(AVG(p.opm_percentage), 2) AS avg_opm_percentage,
       COUNT(*) AS company_count
FROM profitandloss p
JOIN companies c ON c.id = p.company_id
WHERE p.year = (SELECT MAX(year) FROM profitandloss)
GROUP BY c.sector, p.year
ORDER BY avg_opm_percentage DESC;

-- Q06. Latest market-cap ranking
SELECT c.id AS company_id,
       c.company_name,
       m.year,
       m.market_cap,
       m.enterprise_value
FROM market_cap m
JOIN companies c ON c.id = m.company_id
WHERE m.year = (SELECT MAX(year) FROM market_cap)
ORDER BY m.market_cap DESC
LIMIT 10;

-- Q07. Financial-statement year coverage per company
SELECT c.id AS company_id,
       c.company_name,
       COUNT(DISTINCT p.year) AS pnl_years,
       COUNT(DISTINCT b.year) AS balance_sheet_years,
       COUNT(DISTINCT cf.year) AS cashflow_years
FROM companies c
LEFT JOIN profitandloss p ON p.company_id = c.id
LEFT JOIN balancesheet b ON b.company_id = c.id
LEFT JOIN cashflow cf ON cf.company_id = c.id
GROUP BY c.id, c.company_name
ORDER BY pnl_years ASC, balance_sheet_years ASC, cashflow_years ASC, c.id;

-- Q08. Companies with less than five P&L years
SELECT c.id AS company_id,
       c.company_name,
       COUNT(DISTINCT p.year) AS pnl_years
FROM companies c
LEFT JOIN profitandloss p ON p.company_id = c.id
GROUP BY c.id, c.company_name
HAVING COUNT(DISTINCT p.year) < 5
ORDER BY pnl_years, c.id;

-- Q09. Latest stock-price snapshot per company
WITH latest_price AS (
    SELECT company_id, MAX(price_date) AS latest_date
    FROM stock_prices
    GROUP BY company_id
)
SELECT c.id AS company_id,
       c.company_name,
       s.price_date,
       s.close_price,
       s.volume
FROM latest_price lp
JOIN stock_prices s
  ON s.company_id = lp.company_id
 AND s.price_date = lp.latest_date
JOIN companies c ON c.id = s.company_id
ORDER BY s.close_price DESC
LIMIT 10;

-- Q10. Foreign-key integrity check
-- Expected result: zero rows.
PRAGMA foreign_key_check;
