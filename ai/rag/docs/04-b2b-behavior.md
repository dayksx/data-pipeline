# Analysis: B2B purchasing behavior and customer profile

**Dataset:** Online Retail (UK B2B)  
**Customer type:** businesses (B2B) with some consumers  
**Source:** `sales_clean` (hashed PII: `customer_id_hash`)  
**Currency:** GBP (£)

## Executive summary

This dataset does not resemble classic B2C e-commerce. Orders are **massive baskets** (~85 lines per invoice on average, ~350 lines/month in the stable phase), with a small number of monthly invoices (~100) generating a huge volume of lines (~35,000/month). This is the profile of a **wholesaler** selling to resellers or professional accounts.

## Behavioral metrics

| Metric | Value |
|--------|-------|
| Cleaned lines | 8,601 |
| Distinct invoices | 101 |
| Distinct customers (raw) | ~4,302 |
| Customers per country (cleaned) | ~1,415–1,495 per market |
| Average lines per invoice | **~85.2** |
| Lines per invoice in stable phase | **~350** (35k lines / 100 invoices) |

## B2B signature: large baskets, few orders

### B2C vs this dataset

| Criterion | Typical B2C e-commerce | This dataset |
|-----------|------------------------|--------------|
| Lines per order | 1–5 | **85–350** |
| Orders per month | thousands | **~100** |
| Seasonality | Christmas, sales | Stable plateau all year 2011 |
| Buyer type | consumers | **professional accounts** |

### What this implies

- **Average basket** and **order frequency** KPIs must be interpreted in **wholesale** logic, not retail.
- A customer with a given `customer_id_hash` may appear on many lines of the same invoice — this is normal.
- RFM analyses (Recency, Frequency, Monetary) are possible via `customer_id_hash`, but invoice/line grain must be well understood.

## PII anonymization

The pipeline replaces raw `CustomerID` with `customer_id_hash` (SHA-256 + salt) in `transform.py`:

- The column `customer_id` **does not exist** in `sales_clean`.
- Any SQL query or customer analysis must use `customer_id_hash`.
- ~4,300 distinct customers in raw data, ~1,400–1,500 per country after cleaning.

## Billing pattern

In the stable phase (2011), each month has **~100 invoices** for **~35,000 items sold**. Each invoice therefore covers on average **~350 product references** — a wholesale purchase order, not an impulse buy.

The invoice count is **identical per country** (101 each), reinforcing the hypothesis of regional account structure rather than organic customer acquisition.

## Analytical recommendations

1. **Do not apply B2C benchmarks** (conversion rate, cart abandonment) to this dataset.
2. **Segment by `customer_id_hash`** to identify the most active accounts (custom SQL on `sales_clean`).
3. **Aggregate at invoice level** (`invoice_no`) before analyzing order size.
4. **Mention grain** in every report: one row ≠ one order, it is one item in an order.

## Useful columns in `sales_clean`

| Column | B2B usage |
|--------|-----------|
| `invoice_no` | Order / purchase order identifier |
| `customer_id_hash` | Anonymized customer account |
| `quantity` | Purchase volume (always > 0 after cleaning) |
| `country` | Customer account market |
| `sale_month` | Monthly order rhythm |
