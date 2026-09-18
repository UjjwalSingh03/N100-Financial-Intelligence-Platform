-- Sprint 1 Day 04: SQLite database schema
-- The project specification says "10 tables", while the supplied logical
-- table list contains 11 entities. This schema keeps all 11 so no source
-- domain is silently dropped.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY,
    company_name TEXT NOT NULL,
    ticker TEXT,
    bse_code TEXT,
    nse_code TEXT,
    isin TEXT,
    sector TEXT,
    industry TEXT,
    website TEXT
);

CREATE TABLE IF NOT EXISTS profitandloss (
    id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    sales REAL,
    expenses REAL,
    operating_profit REAL,
    opm_percentage REAL,
    other_income REAL,
    interest REAL,
    depreciation REAL,
    profit_before_tax REAL,
    tax REAL,
    net_profit REAL,
    eps REAL,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    UNIQUE (company_id, year)
);

CREATE TABLE IF NOT EXISTS balancesheet (
    id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    equity_capital REAL,
    reserves REAL,
    borrowings REAL,
    other_liabilities REAL,
    total_liabilities REAL,
    fixed_assets REAL,
    investments REAL,
    other_assets REAL,
    total_assets REAL,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    UNIQUE (company_id, year)
);

CREATE TABLE IF NOT EXISTS cashflow (
    id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    cash_from_operating_activity REAL,
    cash_from_investing_activity REAL,
    cash_from_financing_activity REAL,
    net_cash_flow REAL,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    UNIQUE (company_id, year)
);

CREATE TABLE IF NOT EXISTS analysis (
    id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL,
    metric_name TEXT,
    metric_value REAL,
    metric_year INTEGER,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL,
    document_type TEXT,
    document_url TEXT,
    document_date TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS prosandcons (
    id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL,
    item_type TEXT,
    description TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS sectors (
    id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL,
    sector TEXT,
    industry TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS stock_prices (
    id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL,
    price_date TEXT NOT NULL,
    open_price REAL,
    high_price REAL,
    low_price REAL,
    close_price REAL,
    volume REAL,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    UNIQUE (company_id, price_date)
);

CREATE TABLE IF NOT EXISTS financial_ratios (
    id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    ratio_name TEXT,
    ratio_value REAL,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS peer_groups (
    id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL,
    peer_group_name TEXT,
    peer_company_id INTEGER,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    FOREIGN KEY (peer_company_id) REFERENCES companies(id)
);

CREATE INDEX IF NOT EXISTS idx_pnl_company_year ON profitandloss(company_id, year);
CREATE INDEX IF NOT EXISTS idx_bs_company_year ON balancesheet(company_id, year);
CREATE INDEX IF NOT EXISTS idx_cf_company_year ON cashflow(company_id, year);
CREATE INDEX IF NOT EXISTS idx_prices_company_date ON stock_prices(company_id, price_date);
CREATE INDEX IF NOT EXISTS idx_ratios_company_year ON financial_ratios(company_id, year);

PRAGMA foreign_keys = ON;
