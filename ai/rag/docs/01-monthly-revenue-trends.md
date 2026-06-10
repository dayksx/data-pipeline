# Analysis: monthly revenue trends

**Dataset:** Online Retail (UK B2B)  
**Period:** January 2010 → December 2011 (extract truncated on 2011-12-11)  
**Source:** `sales_clean` after cleaning (`spark/jobs/transform.py`)  
**Currency:** GBP (£)

## Executive summary

Total cleaned revenue is **£10,982,247.11** over **24 calendar months**. The monthly series shows **two distinct regimes**: a near-zero startup phase (Jan–Nov 2010), then a stable plateau at ~£840k–£980k/month (Dec 2010–Nov 2011). Any trend analysis must treat these two phases separately.

## Key monthly statistics

| Metric | Value |
|--------|-------|
| Average monthly revenue | £457,593.63 |
| Median monthly revenue | £547,494.00 |
| Strongest month | **August 2011** — £980,746.72 (101 invoices) |
| Weakest month | **May 2010** — £4,363.21 (5 invoices) |
| Monthly standard deviation | £441,542.87 |

> **Note:** standard deviation is close to the mean because 2010 months pull the series down. The **median** is a more reliable central indicator once the ramp-up phase is understood.

## Month-by-month timeline

### Phase 1 — Ramp-up (Jan–Nov 2010)

| Month | Revenue | Invoices | Items sold |
|-------|---------|----------|------------|
| 2010-01 | £4,525.92 | 7 | 267 |
| 2010-02 | £6,603.81 | 3 | 169 |
| 2010-03 | £16,988.08 | 13 | 552 |
| 2010-05 | £4,363.21 | 5 | 164 |
| 2010-11 | £6,106.94 | 6 | 330 |

Revenue between **£4k and £17k** per month, with **3 to 13 invoices**. Activity incompatible with the operational rhythm observed afterwards.

### Phase 2 — Operational plateau (Dec 2010–Nov 2011)

| Month | Revenue | Invoices | Items sold |
|-------|---------|----------|------------|
| 2010-12 | £848,247.18 | 101 | 33,783 |
| 2011-01 | £866,166.80 | 101 | 34,634 |
| 2011-08 | £980,746.72 | 101 | 37,435 |
| 2011-10 | £941,209.01 | 100 | 36,261 |
| 2011-11 | £853,838.63 | 101 | 34,085 |

Revenue stable around **£840k–£980k**, with **~100 invoices/month** and **~35,000 line items/month**. No marked B2C seasonality — rather a recurring wholesale order rhythm.

## Identified anomalies

### 1. Structural jump in December 2010

Revenue: **£6,107 (Nov 2010) → £848,247 (Dec 2010)** — multiplied by **~140×**. Invoices: 6 → 101.

Possible hypotheses:
- change in extract scope;
- effective launch of a sales channel;
- migration to a new billing system.

**Analytical impact:** do not use Jan–Nov 2010 as a baseline for YoY comparisons.

### 2. Incomplete December 2011

Revenue of only **£252,388** (90 invoices) while previous months run around £850k–£940k. The CSV extract ends on **December 11, 2011**. This month is **truncated** and does not reflect a real drop in activity.

### 3. Slight upward drift in 2011

Within the plateau, revenue progresses from ~£866k (Jan 2011) to a peak of ~£981k (Aug 2011), then oscillates. Slightly positive trend, with no abrupt break before the end of the extract.

## Reporting recommendations

1. Segment dashboards into **pre-Dec 2010** vs **post-Dec 2010**.
2. Exclude or annotate **December 2011** in trend charts.
3. Prefer the **median** over the mean for monthly KPIs.
4. Use the gold table `monthly_sales` for pre-computed trends.

## Related Postgres tables

- `public.monthly_sales` — monthly series (revenue, invoices, items)
- `public.monthly_stats` — descriptive statistics on the monthly series
- `public.total_revenue` — global aggregate (£10,982,247.11)
