"""Refresh RAG markdown reports from Postgres when the warehouse changes.

Flow (daily cron or Airflow after Spark analysis):
  1. fingerprint = row count + total revenue on sales_clean
  2. if fingerprint changed → rewrite ai/rag/docs/*.md
  3. python rag/jobs/index.py

State: <rag_docs_dir>/../.warehouse_state.json (e.g. data/rag/ in Airflow)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

_JOBS_DIR = Path(__file__).resolve().parent
_AI_SRC = _JOBS_DIR.parents[1] / "src"
sys.path.insert(0, str(_AI_SRC))

from insights_agent.config import get_settings  # noqa: E402


# --- helpers -----------------------------------------------------------------

def gbp(value: Any) -> str:
    return f"£{float(value or 0):,.2f}"


def month_str(value: Any) -> str:
    return str(value)[:7] if value else "n/a"


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    out.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(out)


def query_one(conn: psycopg.Connection, sql: str) -> dict[str, Any]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql)
        row = cur.fetchone()
    return dict(row) if row else {}


def query_all(conn: psycopg.Connection, sql: str) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql)
        return [dict(r) for r in cur.fetchall()]


def header(title: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"# {title}\n\n**Source:** live SQL on `sales_clean` / gold tables  \n**Generated:** {ts}\n"


# --- change detection --------------------------------------------------------

def fetch_fingerprint(conn: psycopg.Connection) -> dict[str, Any]:
    """Cheap check: did Spark reload the warehouse since last run?"""
    row = query_one(
        conn,
        """
        SELECT COUNT(*)::bigint AS row_count,
               COALESCE(ROUND(SUM(revenue)::numeric, 2), 0) AS total_revenue
        FROM sales_clean
        """,
    )
    return {k: float(v) if isinstance(v, Decimal) else v for k, v in row.items()}


def state_file(docs_dir: Path) -> Path:
    return docs_dir.parent / ".warehouse_state.json"


def load_state(docs_dir: Path) -> dict[str, Any] | None:
    path = state_file(docs_dir)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(docs_dir: Path, fingerprint: dict[str, Any]) -> None:
    path = state_file(docs_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"fingerprint": fingerprint, "updated_at": datetime.now(timezone.utc).isoformat()}, indent=2),
        encoding="utf-8",
    )


def warehouse_changed(current: dict[str, Any], previous: dict[str, Any] | None) -> bool:
    return previous is None or current != previous.get("fingerprint")


# --- report writers (one function = one .md file) ---------------------------

def write_monthly_revenue(conn: psycopg.Connection) -> str:
    stats = query_one(conn, "SELECT * FROM monthly_stats")
    months = query_all(
        conn,
        "SELECT sale_month, revenue, invoices_count, items_sold FROM monthly_sales ORDER BY sale_month",
    )
    total = query_one(conn, "SELECT total_revenue FROM total_revenue")

    month_rows = [
        [month_str(m["sale_month"]), gbp(m["revenue"]), str(m["invoices_count"]), str(m["items_sold"])]
        for m in months
    ]

    return header("Analysis: monthly revenue trends") + f"""
## Executive summary

Total revenue: **{gbp(total.get('total_revenue', 0))}** over **{len(months)}** months.
Known anomalies (from semantic layer): step change in Dec 2010, partial Dec 2011.

## Gold KPIs (monthly_stats)

{md_table(
    ["Metric", "Value"],
    [
        ["Average monthly revenue", gbp(stats.get("avg_monthly_revenue"))],
        ["Median monthly revenue", gbp(stats.get("median_monthly_revenue"))],
        ["Peak month revenue", gbp(stats.get("peak_monthly_revenue"))],
        ["Lowest month revenue", gbp(stats.get("lowest_monthly_revenue"))],
        ["Std dev", gbp(stats.get("standard_deviation_monthly_revenue"))],
    ],
)}

## Monthly series (monthly_sales)

{md_table(["Month", "Revenue", "Invoices", "Items"], month_rows)}

## Notes for the agent

- Use `run_gold_query("monthly_revenue_trend")` for live numbers.
- Do not compare Jan–Nov 2010 with 2011 without segmenting (ramp-up vs plateau).
- December 2011 may be incomplete (extract end date).
"""


def write_product_performance(conn: psycopg.Connection) -> str:
    products = query_all(
        conn,
        "SELECT stock_code, description, total_quantity, total_revenue FROM top_products ORDER BY total_quantity DESC",
    )
    rows = [
        [str(i), str(p["stock_code"]), str(p.get("description") or ""), str(p["total_quantity"]), gbp(p["total_revenue"])]
        for i, p in enumerate(products, start=1)
    ]

    return header("Analysis: product performance and bestsellers") + f"""
## Executive summary

Top products by **quantity** (gold table `top_products`). Volume leaders are not always revenue leaders.

## Top 10 by quantity

{md_table(["Rank", "Stock code", "Description", "Quantity", "Revenue"], rows)}

## Notes for the agent

- Fixed KPI: `run_gold_query("top_products_by_quantity")`.
- Custom monthly ranking: SQL on `sales_clean` with `ROW_NUMBER()` (see `postgres/queries/analysis.sql`).
"""


def write_geographic(conn: psycopg.Connection) -> str:
    countries = query_all(
        conn,
        """
        SELECT country,
               ROUND(SUM(revenue)::numeric, 2) AS revenue,
               COUNT(*) AS lines,
               COUNT(DISTINCT customer_id_hash) AS customers
        FROM sales_clean
        GROUP BY country
        ORDER BY revenue DESC
        """,
    )
    rows = [[c["country"], gbp(c["revenue"]), str(c["lines"]), str(c["customers"])] for c in countries]

    return header("Analysis: geographic distribution") + f"""
## Revenue by country (sales_clean)

{md_table(["Country", "Revenue", "Lines", "Customers"], rows)}

## Notes for the agent

- Markets are relatively balanced (~£2.1M each for top 5).
- `country = 'Utopia'` is excluded in `transform.py` (test data).
- Australia rolling average: 2nd query in `postgres/queries/analysis.sql`.
"""


def write_b2b(conn: psycopg.Connection) -> str:
    s = query_one(
        conn,
        """
        SELECT COUNT(*) AS lines,
               COUNT(DISTINCT invoice_no) AS invoices,
               COUNT(DISTINCT customer_id_hash) AS customers,
               ROUND(AVG(unit_price)::numeric, 2) AS avg_unit_price
        FROM sales_clean
        """,
    )
    lines_per_invoice = query_one(
        conn,
        """
        SELECT ROUND(AVG(cnt)::numeric, 1) AS avg_lines_per_invoice
        FROM (SELECT COUNT(*) AS cnt FROM sales_clean GROUP BY invoice_no) t
        """,
    )

    return header("Analysis: B2B behavior") + f"""
## Executive summary

Wholesale profile: few invoices, large baskets. Not typical B2C e-commerce.

## Metrics

{md_table(
    ["Metric", "Value"],
    [
        ["Line items", f"{s.get('lines', 0):,}"],
        ["Distinct invoices", f"{s.get('invoices', 0):,}"],
        ["Distinct customers", f"{s.get('customers', 0):,}"],
        ["Avg unit price", gbp(s.get("avg_unit_price"))],
        ["Avg lines per invoice", str(lines_per_invoice.get("avg_lines_per_invoice", "n/a"))],
    ],
)}

## Notes for the agent

- Use `customer_id_hash` — column `customer_id` does not exist in `sales_clean`.
- Aggregate by `invoice_no` before measuring order size.
"""


def write_data_quality(conn: psycopg.Connection) -> str:
    p = query_one(
        conn,
        """
        SELECT COUNT(*) AS lines,
               COUNT(DISTINCT stock_code) AS products,
               COUNT(DISTINCT country) AS countries,
               ROUND(SUM(revenue)::numeric, 2) AS revenue,
               MIN(sale_date)::text AS min_date,
               MAX(sale_date)::text AS max_date
        FROM sales_clean
        """,
    )

    return header("Analysis: data quality and cleaning") + f"""
## Cleaned snapshot (sales_clean)

{md_table(
    ["Metric", "Value"],
    [
        ["Lines", f"{p.get('lines', 0):,}"],
        ["Products", f"{p.get('products', 0):,}"],
        ["Countries", str(p.get("countries", 0))],
        ["Revenue", gbp(p.get("revenue"))],
        ["Date range", f"{p.get('min_date')} → {p.get('max_date')}"],
    ],
)}

## Cleaning rules (transform.py)

1. Drop cancellations (`InvoiceNo` starts with `C`)
2. Drop nulls on key columns
3. Keep `quantity > 0` and `unit_price >= 0`
4. Exclude `country = 'Utopia'`
5. Deduplicate rows
6. Hash `CustomerID` → `customer_id_hash`
7. Recompute `revenue = quantity × unit_price`

## Notes for the agent

- Official KPIs always from `sales_clean`, never the raw CSV.
- Gold `total_revenue` must match `SUM(revenue)` on `sales_clean`.
"""


REPORTS: list[tuple[str, Any]] = [
    ("01-monthly-revenue-trends.md", write_monthly_revenue),
    ("02-product-performance.md", write_product_performance),
    ("03-geographic-distribution.md", write_geographic),
    ("04-b2b-behavior.md", write_b2b),
    ("05-data-quality-cleaning.md", write_data_quality),
]


def generate_reports(docs_dir: Path, conn: psycopg.Connection) -> list[str]:
    docs_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for filename, writer in REPORTS:
        (docs_dir / filename).write_text(writer(conn), encoding="utf-8")
        written.append(filename)
    return written


def run(*, force: bool = False, check_only: bool = False) -> dict[str, Any]:
    settings = get_settings()

    docs_dir = settings.rag_docs_dir

    with psycopg.connect(settings.postgres_dsn, row_factory=dict_row) as conn:
        fingerprint = fetch_fingerprint(conn)
        previous = load_state(docs_dir)
        changed = force or warehouse_changed(fingerprint, previous)

        if check_only:
            return {"changed": changed, "fingerprint": fingerprint, "docs_dir": str(docs_dir)}

        if not changed:
            return {"updated": False, "reason": "warehouse unchanged", "fingerprint": fingerprint}

        docs_dir.mkdir(parents=True, exist_ok=True)
        files = generate_reports(docs_dir, conn)
        save_state(docs_dir, fingerprint)

    return {"updated": True, "files": files, "fingerprint": fingerprint, "next_step": "python rag/jobs/index.py"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate RAG .md reports when SQL warehouse changes")
    parser.add_argument("--force", action="store_true", help="Rewrite even if fingerprint unchanged")
    parser.add_argument("--check-only", action="store_true", help="Only print whether warehouse changed")
    args = parser.parse_args()
    print(json.dumps(run(force=args.force, check_only=args.check_only), indent=2, default=str))


if __name__ == "__main__":
    main()
