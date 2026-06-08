import pytest

from insights_agent.tools import validate_sql


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT COUNT(*) FROM public.sales_clean",
        "SELECT country, SUM(revenue) FROM sales_clean GROUP BY country",
    ],
)
def test_validate_accepts_readonly_queries(sql: str) -> None:
    result = validate_sql(sql)
    assert result.ok, result.errors
    assert result.sql is not None
    assert "LIMIT" in result.sql.upper()


def test_validate_adds_limit_when_missing() -> None:
    result = validate_sql("SELECT 1")
    assert result.ok
    assert "LIMIT 500" in result.sql.upper()


def test_validate_caps_oversized_limit() -> None:
    result = validate_sql("SELECT 1 LIMIT 1000")
    assert result.ok
    assert "LIMIT 500" in result.sql.upper()


@pytest.mark.parametrize(
    "sql",
    [
        "",
        "DROP TABLE sales_clean",
        "SELECT * FROM users",
        "SELECT 1; SELECT 2",
        "SELEC 1 FROM sales_clean",
    ],
)
def test_validate_rejects_bad_sql(sql: str) -> None:
    result = validate_sql(sql)
    assert not result.ok
    assert result.errors
