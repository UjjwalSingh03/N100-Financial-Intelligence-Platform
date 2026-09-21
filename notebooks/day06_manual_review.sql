-- Sprint 1 Day 06: Data Quality Manual Review
-- Run against nifty100.db after Day 05 make load.
-- The queries are read-only and use the actual source-aligned table names.

-- 1) Select five deterministic "random" companies for manual review.
-- Using a stable hash-like ordering keeps the same five companies reproducible.
WITH ranked AS (
    SELECT
        id,
        company_name,
        ROW_NUMBER() OVER (ORDER BY length(id), id) AS rn
    FROM companies
)
SELECT id, company_name
FROM ranked
WHERE rn IN (7, 25, 43, 61, 79)
ORDER BY rn;

-- 2) Year coverage for the five review companies.
WITH review_companies AS (
    SELECT id
    FROM (
        SELECT id, ROW_NUMBER() OVER (ORDER BY length(id), id) AS rn
        FROM companies
    )
    WHERE rn IN (7, 25, 43, 61, 79)
)
SELECT
    c.id AS company_id,
    c.company_name,
    MIN(p.year) AS pnl_first_year,
    MAX(p.year) AS pnl_last_year,
    COUNT(DISTINCT p.year) AS pnl_years,
    MIN(b.year) AS balance_first_year,
    MAX(b.year) AS balance_last_year,
    COUNT(DISTINCT b.year) AS balance_years,
    MIN(cf.year) AS cashflow_first_year,
    MAX(cf.year) AS cashflow_last_year,
    COUNT(DISTINCT cf.year) AS cashflow_years
FROM companies c
JOIN review_companies r ON r.id = c.id
LEFT JOIN profit_and_loss p ON p.company_id = c.id
LEFT JOIN balance_sheet b ON b.company_id = c.id
LEFT JOIN cash_flow cf ON cf.company_id = c.id
GROUP BY c.id, c.company_name
ORDER BY c.id;

-- 3) Identify companies with fewer than five P&L years.
SELECT
    c.id AS company_id,
    c.company_name,
    COUNT(DISTINCT p.year) AS pnl_years,
    MIN(p.year) AS first_year,
    MAX(p.year) AS last_year
FROM companies c
LEFT JOIN profit_and_loss p ON p.company_id = c.id
GROUP BY c.id, c.company_name
HAVING COUNT(DISTINCT p.year) < 5
ORDER BY pnl_years, c.id;

-- 4) Compare annual coverage across the three core financial statements.
SELECT
    c.id AS company_id,
    c.company_name,
    COUNT(DISTINCT p.year) AS pnl_years,
    COUNT(DISTINCT b.year) AS balance_years,
    COUNT(DISTINCT cf.year) AS cashflow_years
FROM companies c
LEFT JOIN profit_and_loss p ON p.company_id = c.id
LEFT JOIN balance_sheet b ON b.company_id = c.id
LEFT JOIN cash_flow cf ON cf.company_id = c.id
GROUP BY c.id, c.company_name
HAVING MIN(
    COUNT(DISTINCT p.year),
    COUNT(DISTINCT b.year),
    COUNT(DISTINCT cf.year)
) < 5
ORDER BY c.id;

-- 5) Detect orphan company IDs. A clean Day 05/06 database should return
-- zero rows from every query below.
SELECT DISTINCT p.company_id
FROM profit_and_loss p
LEFT JOIN companies c ON c.id = p.company_id
WHERE c.id IS NULL
ORDER BY p.company_id;

SELECT DISTINCT b.company_id
FROM balance_sheet b
LEFT JOIN companies c ON c.id = b.company_id
WHERE c.id IS NULL
ORDER BY b.company_id;

SELECT DISTINCT cf.company_id
FROM cash_flow cf
LEFT JOIN companies c ON c.id = cf.company_id
WHERE c.id IS NULL
ORDER BY cf.company_id;

SELECT DISTINCT fr.company_id
FROM financial_ratios fr
LEFT JOIN companies c ON c.id = fr.company_id
WHERE c.id IS NULL
ORDER BY fr.company_id;

SELECT DISTINCT d.company_id
FROM documents d
LEFT JOIN companies c ON c.id = d.company_id
WHERE c.id IS NULL
ORDER BY d.company_id;

SELECT DISTINCT a.company_id
FROM analysis a
LEFT JOIN companies c ON c.id = a.company_id
WHERE c.id IS NULL
ORDER BY a.company_id;

SELECT DISTINCT pc.company_id
FROM pros_and_cons pc
LEFT JOIN companies c ON c.id = pc.company_id
WHERE c.id IS NULL
ORDER BY pc.company_id;

-- 6) Final compact coverage summary.
SELECT
    COUNT(*) AS total_companies,
    SUM(CASE WHEN pnl_years < 5 THEN 1 ELSE 0 END) AS companies_under_5_pnl_years,
    MIN(pnl_years) AS minimum_pnl_years,
    MAX(pnl_years) AS maximum_pnl_years,
    ROUND(AVG(pnl_years), 2) AS average_pnl_years
FROM (
    SELECT c.id, COUNT(DISTINCT p.year) AS pnl_years
    FROM companies c
    LEFT JOIN profit_and_loss p ON p.company_id = c.id
    GROUP BY c.id
);
