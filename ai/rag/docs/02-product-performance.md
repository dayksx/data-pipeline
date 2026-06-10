# Analysis: product performance and bestsellers

**Dataset:** Online Retail (UK B2B)  
**Grain:** one row = one item on an invoice  
**Source:** `sales_clean` / gold table `top_products`  
**Currency:** GBP (£)

## Executive summary

The catalog contains **~7,100 distinct product codes** (stock codes) in raw data, reduced after cleaning. Sales are **highly concentrated**: the top 10 by quantity represents a significant share of total volume. Rankings by **quantity** and by **revenue** diverge — the most sold products by units are not necessarily the most profitable.

## Top 10 products by quantity sold (global)

| Rank | Stock code | Description | Quantity | Revenue |
|------|------------|-------------|----------|---------|
| 1 | 80595 | Product 80595 | 332 | £10,037.26 |
| 2 | 80502 | Product 80502 | 324 | £5,295.78 |
| 3 | 71319 | Product 71319 | 307 | £6,416.71 |
| 4 | 73901 | Product 73901 | 305 | £5,808.28 |
| 5 | 76668 | Product 76668 | 298 | £7,847.02 |

**Observation:** product #1 (80595) generates the most volume **and** the most revenue in the top 5. Product #2 (80502) sells almost as many units but generates **half the revenue** — significantly lower unit price.

## Average unit price

On valid sales lines, the average unit price is approximately **£25**. Mid-range positioning for gifts / household items, consistent with the distributor's B2B positioning.

## Monthly revenue leaders (last 6 months)

Monthly bestsellers **change each month** when ranked by revenue — unlike the global top by quantity which is stable.

### July 2011

| Rank | Stock code | Monthly revenue |
|------|------------|-----------------|
| 1 | 81364 | £6,751.16 |
| 2 | 79000 | £4,871.00 |
| 3 | 79886 | £4,831.40 |

### August 2011 (record month)

| Rank | Stock code | Monthly revenue |
|------|------------|-----------------|
| 1 | 76117 | £8,269.94 |
| 2 | 75635 | £7,262.48 |
| 3 | 81323 | £6,241.93 |

### October 2011

| Rank | Stock code | Monthly revenue |
|------|------------|-----------------|
| 1 | 79778 | £6,114.33 |
| 2 | 76365 | £5,514.11 |
| 3 | 80946 | £5,310.34 |

**Insight:** no product dominates the monthly revenue ranking for long. The portfolio is **rotating** — typical of a wholesaler with a broad assortment and varied recurring orders.

## Business implications

1. **Stock planning:** the global top by quantity (80595, 80502) deserves priority attention for availability.
2. **Pricing:** flag high-volume / low-revenue unit products (80502) for margin actions.
3. **Reporting:** distinguish **volume** KPIs (quantity) and **value** KPIs (revenue) — they answer different questions.
4. **Ad-hoc analysis:** use `sales_clean` grouped by `stock_code` and `sale_month` for custom rankings.

## Useful queries

- Fixed KPI: `run_gold_query("top_products_by_quantity")` → table `public.top_products`
- Monthly ranking: SQL on `sales_clean` with `ROW_NUMBER() OVER (PARTITION BY sale_month ORDER BY revenue DESC)`

## Related Postgres tables

- `public.top_products` — global top 10 by quantity
- `public.sales_clean` — line-level grain for custom product analysis
