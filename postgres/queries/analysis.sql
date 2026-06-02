-- Identify the top 3 products by revenue for each month over the last 6 months:
-- Step 1: monthly_product: group by sale_month and stock_code to get the revenue for each product in each month
-- Step 2: ranked_monthly_product: rank the products by revenue for each month
-- Step 3: select the top 3 products by revenue for each month

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

-- Calculate the rolling 3-month Average Revenue for 'Australia':
-- Step 1: get the total monthly revenue
-- Step 2: get the rolling 3-month average revenue = mean of current month + 2 preceding months

WITH 
    monthly_revenue AS (
        SELECT sale_month, ROUND(SUM(revenue)::numeric, 2) AS monthly_revenue
        FROM sales_clean
        WHERE country = 'Australia'
        GROUP BY sale_month
    )
SELECT sale_month, monthly_revenue, ROUND(AVG(monthly_revenue) 
    OVER (
        ORDER BY sale_month
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)::numeric, 2
    ) AS rolling_3m_avg_revenue
FROM monthly_revenue
ORDER BY sale_month ASC;

