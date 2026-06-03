import os
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

BASE = os.getenv("PIPELINE_ROOT", "/opt/pipeline")
postgres_host = os.getenv("POSTGRES_HOST", "localhost")
postgres_db = os.getenv("POSTGRES_DB", "pipeline")
postgres_user = os.getenv("POSTGRES_USER", "postgres")
postgres_password = os.getenv("POSTGRES_PASSWORD", "postgres")

input_path = f"{BASE}/data/silver/retails_clean"
output_path = f"{BASE}/data/gold/retails_analysis"

def main() -> None:
    spark = SparkSession.builder.appName("analysis").config("spark.sql.session.timeZone", "UTC").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    try:
        # Read input file
        cleaned_df = spark.read.parquet(input_path)

        # Total revenue
        total_revenue_df = cleaned_df.agg(F.round(F.sum("revenue"), 2).alias("total_revenue"))
        print(f"📊 [analysis] Total revenue: {total_revenue_df.first()['total_revenue']}")
        
        # Top 10 most popular products based on the quantity sold
        top_products_df = (
            cleaned_df
            .groupBy("stock_code")
            .agg(
                F.first("description").alias("description"),
                F.sum("quantity").alias("total_quantity"),
                F.round(F.sum("revenue"), 2).alias("total_revenue"),
            )
            .orderBy(F.desc("total_quantity"), F.desc("total_revenue"))
            .limit(10)
        )
        print("📊 [analysis] Top 10 most popular products:")
        top_products_df.show(10)

        # Monthly revenue trend
        monthly_sales_df = (
            cleaned_df
            .groupBy(F.date_trunc("month", F.col("sale_date")).alias("sale_month"))
            .agg(
                F.countDistinct("invoice_no").alias("invoices_count"),
                F.round(F.sum("revenue"), 2).alias("revenue"),
                F.sum("quantity").alias("items_sold"),
            )
            .select("sale_month", "invoices_count", "revenue", "items_sold")
        )

        print("📊 [analysis] Monthly revenue trend:")
        monthly_sales_df.orderBy("sale_month").show(24)
        print("📊 [analysis] Monthly revenue trend (best months first):")
        monthly_sales_df.orderBy(F.desc("revenue")).show(24)

        # Monthly revenue trend statistics
        monthly_stats_df = monthly_sales_df.agg(
            F.round(F.avg("revenue"), 2).alias("avg_monthly_revenue"),
            F.round(F.median("revenue"), 2).alias("median_monthly_revenue"),
            F.round(F.max("revenue"), 2).alias("peak_monthly_revenue"),
            F.round(F.min("revenue"), 2).alias("lowest_monthly_revenue"),
            F.round(F.stddev_samp("revenue"), 2).alias("standard_deviation_monthly_revenue"),
        )

        print("📊 [analysis] Monthly revenue summary:")
        monthly_stats_df.show(truncate=False)

        for data in [
            {"table": "total_revenue", "dataframe": total_revenue_df},
            {"table": "top_products", "dataframe": top_products_df},
            {"table": "monthly_sales", "dataframe": monthly_sales_df},
            {"table": "monthly_stats", "dataframe": monthly_stats_df},
        ]:
            # Write parquet
            (
                data["dataframe"].write.format("parquet")
                .mode("overwrite")
                .save(f"{output_path}/{data['table']}")
            )
            # Write in Postgres
            (
                data["dataframe"].write.format("jdbc").mode("overwrite")
                .option("url", f"jdbc:postgresql://{postgres_host}:5432/{postgres_db}")
                .option("dbtable", f"public.{data['table']}")
                .option("user", postgres_user)
                .option("password", postgres_password)
                .option("driver", "org.postgresql.Driver")
                .save()
            )
            print(
                f"🚀 [analysis] Wrote public.{data['table']} → {output_path}/{data['table']}/ (parquet + jdbc)"
            )
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
