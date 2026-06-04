# SQL analysis: query methodology

All queries operate on **`public.sales_clean`**, where each row represents one product line on an invoice. The executable SQL is provided in [`analysis.sql`](analysis.sql).

---

## Query 1: Top 3 products by revenue, per month (last 6 months)

**Objective:** For each month within the **last 6 months of the dataset**, return the **three products with the highest revenue**.

| Step | Action | Rationale |
|------|--------|-----------|
| 1 | Restrict rows to the last 6 months relative to the maximum `sale_month` in the data | Meets the exercise requirement for a 6-month window |
| 2 | Aggregate with `GROUP BY sale_month, stock_code`, compute `SUM(revenue)`, and retain one `description` (e.g. `MAX`) | Produces one revenue total per product per month |
| 3 | Assign ranks per month using `ROW_NUMBER() OVER (PARTITION BY sale_month ORDER BY revenue DESC)` | Ranking is calculated independently for each month |
| 4 | Filter results where `rank <= 3` | Returns exactly three products per month |

**Query structure:** filter by date range → aggregate by month and product → rank within each month → retain top 3.

---

## Query 2: Rolling 3-month average revenue (Australia)

**Objective:** For **Australia only**, return monthly revenue together with the **3-month moving average** (current month plus the two preceding months).

| Step | Action | Rationale |
|------|--------|-----------|
| 1 | Apply `WHERE country = 'Australia'` | Restricts analysis to Australian customers |
| 2 | Aggregate with `GROUP BY sale_month` and `SUM(revenue)` | Computes one monthly total rather than line-level values |
| 3 | Calculate `AVG(...) OVER (ORDER BY sale_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)` | Defines a 3-month rolling average |

**Query structure:** filter by country → aggregate by month → apply moving average over 3 months.

For the first one or two months, fewer than three months are available in the window. This is expected behavior for a rolling average.

---

## Execution

From the project root, after `transform.py` has loaded `sales_clean`:

```bash
docker exec -i pipeline-postgres psql -U postgres -d pipeline < postgres/queries/analysis.sql
```

For full stack setup and Spark job execution, refer to the [main README](../../README.md).
