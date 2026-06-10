# Analysis: data quality and cleaning impact

**Dataset:** Online Retail (UK B2B)  
**Pipeline:** bronze → silver (`spark/jobs/transform.py`)  
**Target table:** `public.sales_clean`  
**Currency:** GBP (£)

## Executive summary

The source file `data/retails.csv` contains **10,500 lines** for ~£12.5M gross revenue. After cleaning, **8,601 lines** remain for **£10,982,247.11** revenue. Approximately **18% of lines** are excluded — mainly cancellations, invalid quantities, and test data. Cleaning is **critical**: raw KPIs overestimate actual revenue.

## Source file profile

| Metric | Raw value |
|--------|-----------|
| Total lines | 10,500 |
| Period | Jan 12, 2010 → Dec 11, 2011 |
| Distinct invoices (excl. cancellations) | ~102 |
| Distinct customers | ~4,302 |
| Distinct products | ~7,122 |
| Countries | 6 (including Utopia = test) |
| Gross revenue (all lines) | ~£12.5M |

## Identified quality issues

### 1. Cancellations (~5% of lines)

| Issue | Volume | Cleaning rule |
|-------|--------|---------------|
| Cancelled invoices (`InvoiceNo` starts with `C`) | **521 lines (5.0%)** | Excluded in `transform.py` |

Cancellations would skew net revenue if included. In B2B, credit notes and cancellations are frequent — they must be handled separately, not mixed with sales.

### 2. Missing values (~1–2% per column)

| Column | Null lines |
|--------|------------|
| InvoiceNo | 116 |
| StockCode | 114 |
| Quantity | 117 |
| InvoiceDate | 117 |
| UnitPrice | 115 |
| CustomerID | 116 |
| Country | 114 |
| Revenue | 232 |

Lines with nulls on key columns are **dropped** — they would break joins and customer/product metrics.

### 3. Invalid quantities (~2.2%)

| Issue | Volume | Impact |
|-------|--------|--------|
| Quantity ≤ 0 | **235 lines** | Returns, adjustments, or data entry errors |

Only lines with `quantity > 0` are kept. Returns are not modeled separately in the silver layer.

### 4. Test geography

| Issue | Volume | Rule |
|-------|--------|------|
| `country = 'Utopia'` | **115 lines** | Excluded — test value |

Including Utopia would skew market reports.

### 5. Negative prices

A few lines with `unit_price < 0` exist in raw data. The `unit_price >= 0` filter excludes them.

### 6. Duplicates

Deduplication on key: `(customer_id_hash, invoice_no, stock_code, invoice_date, quantity)`.

## Cleaning impact on KPIs

| Metric | Before cleaning | After cleaning | Delta |
|--------|----------------|----------------|-------|
| Lines | 10,500 | 8,601 | **−18%** |
| Revenue | ~£12.5M (raw) / ~£11.7M (basic exclusions) | **£10,982,247.11** | ~−12 to −15% |

> Cleaned revenue is **recomputed**: `revenue = round(quantity × unit_price, 2)` — the pipeline does not trust the source `Revenue` column.

## Rules applied in `transform.py`

1. Exclude `InvoiceNo` starting with `C` (cancellations)
2. Drop nulls on key columns
3. Filter `quantity > 0` and `unit_price >= 0`
4. Exclude `country = 'Utopia'`
5. Deduplicate on composite key
6. Hash `CustomerID` → `customer_id_hash` (SHA-256 + salt, PII removed)
7. Recompute `revenue`, derive `sale_date` and `sale_month`

## Recommendations

1. **Always query `sales_clean`**, never the raw CSV, for official KPIs.
2. **Document exclusions** in every report — 18% fewer lines changes conclusions.
3. **Handle cancellations separately** if a "net revenue after returns" KPI is required.
4. **Verify consistency:** gold `total_revenue` = `SUM(revenue)` on `sales_clean`.

## Related Postgres tables

- `public.sales_clean` — cleaned silver layer (source of truth)
- `public.total_revenue` — sanity check: must equal the sum of `sales_clean.revenue`
