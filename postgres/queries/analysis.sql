-- Identify the top 3 products by revenue for each month over the last 6 months

WITH 
    monthly_product AS (
        SELECT sale_month, stock_code, MAX(description) AS description, ROUND(SUM(revenue)::numeric, 2) AS revenue
        FROM sales_clean
        WHERE sale_month >= (
            SELECT MAX(sale_month) - interval '6 months'
            FROM sales_clean
        )
        GROUP BY sale_month, stock_code
    ),
    ranked_monthly_product AS (
        SELECT *, ROW_NUMBER() OVER (PARTITION BY sale_month ORDER BY revenue DESC) AS rank
        FROM monthly_product
)
SELECT *
FROM ranked_monthly_product
WHERE rank <= 3
ORDER BY sale_month DESC, rank ASC;
