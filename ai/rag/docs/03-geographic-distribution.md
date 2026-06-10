# Analysis: geographic distribution and market mix

**Dataset:** Online Retail (UK B2B)  
**Key field:** `country` (customer country)  
**Source:** `sales_clean`  
**Currency:** GBP (£)

## Executive summary

Despite a **United Kingdom**-based company, revenue is **remarkably balanced** across the five main markets — each contributes approximately **£2.1M–£2.3M**. The UK is not dominant: ~20% of lines only. This is an **export / international wholesale** profile, not a classic domestic retailer.

## Revenue by country (cleaned data)

| Country | Total revenue | Lines | Distinct customers | Invoices |
|---------|--------------|-------|-------------------|----------|
| **Germany** | £2,300,324.44 | 1,768 | 1,479 | 101 |
| **Australia** | £2,182,974.86 | 1,671 | 1,415 | 101 |
| **France** | £2,175,057.11 | 1,694 | 1,439 | 101 |
| **Norway** | £2,170,439.14 | 1,761 | 1,495 | 101 |
| **United Kingdom** | £2,153,451.56 | 1,707 | 1,436 | 101 |

**Cleaned total:** £10,982,247.11 — the sum of the five countries covers 100% of post-cleaning revenue.

## Key observations

### 1. Parity across markets

The gap between the highest country (Germany, £2.30M) and the lowest (UK, £2.15M) is only **~7%**. No market represents more than 21% of the total.

### 2. Same invoice count per country

Each country has exactly **101 distinct invoices**. This suggests a **structural distribution** of orders — possibly an extract pattern or B2B regional account split, not an organic demand distribution.

### 3. UK = domestic market but not the leader

The United Kingdom, the company's home market, ranks **last in revenue**. For executive reporting, the "domestic leader" narrative does not apply to this dataset.

### 4. Excluded country: Utopia

**115 lines** with `country = 'Utopia'` were filtered during cleaning (`transform.py`). This is a test / junk value that would skew geographic KPIs if kept.

## Focus: Australia and 3-month moving average

Australia follows the same global pattern — jump in Dec 2010, plateau in 2011.

| Month | Australia revenue | 3-month moving average |
|-------|------------------|------------------------|
| 2010-11 | £180.70 | £1,671.34 |
| 2010-12 | £161,546.37 | £55,341.99 |
| 2011-06 | £211,471.81 | £177,569.01 |
| 2011-08 | £166,334.90 | £194,846.85 |
| 2011-12 | £47,848.06 | £137,396.85 |

In 2011, monthly Australian revenue stabilizes around **£155k–£212k**, with a moving average around **£175k–£195k** mid-year. December 2011 is incomplete (truncated extract).

## Business implications

1. **Marketing campaigns:** treat all 5 markets as **equal in importance**, not UK-first.
2. **Logistics:** multi-country distribution implies international shipping costs to model.
3. **Country analysis:** filter `sales_clean` with `WHERE country = '...'` for custom breakdowns.
4. **Watch the 101 invoices/country:** verify whether this is an extract artifact before drawing operational conclusions.

## Tables and queries

- Table: `public.sales_clean` (column `country`)
- Australia rolling average query: `postgres/queries/analysis.sql` (2nd query)
- No dedicated gold table per country — ad-hoc analysis via SQL
