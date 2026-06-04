import os
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

BASE = os.getenv("PIPELINE_ROOT", "/opt/pipeline")
postgres_host = os.getenv("POSTGRES_HOST", "postgres")
postgres_db = os.getenv("POSTGRES_DB", "pipeline")
postgres_user = os.getenv("POSTGRES_USER", "postgres")
postgres_password = os.getenv("POSTGRES_PASSWORD", "postgres")

input_path = f"{BASE}/data/bronze/retails_raw"
output_path = f"{BASE}/data/silver/retails_clean"
SALT = os.getenv("PII_HASH_SALT", "secret")

def main() -> None:
    spark = SparkSession.builder.appName("transform").config("spark.sql.session.timeZone", "UTC").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    try:
        # Read input file
        normalized_df = spark.read.parquet(input_path)
        cleaned_df = normalized_df

        cleaned_df = (
            cleaned_df
            # Rename columns to snake_case
            .withColumnsRenamed({
                "InvoiceNo": "invoice_no",
                "StockCode": "stock_code",
                "Description": "description",
                "Quantity": "quantity",
                "InvoiceDate": "invoice_date",
                "UnitPrice": "unit_price",
                "CustomerID": "customer_id",
                "Country": "country",
                "Revenue": "revenue_source",
            })

            # Cast columns to the correct type
            .withColumns({
                "invoice_no": F.col("invoice_no").cast("string"),
                "stock_code": F.col("stock_code").cast("long").cast("string"),
                "description": F.col("description").cast("string"),
                "quantity": F.col("quantity").cast("double"),
                "invoice_date": F.to_timestamp(F.col("invoice_date"), "yyyy-MM-dd HH:mm:ss"),
                "unit_price": F.col("unit_price").cast("double"),
                "customer_id": F.col("customer_id").cast("long"),
                "country": F.col("country").cast("string"),
            })

            # Filter out null values
            .filter(
                (~F.col("invoice_no").startswith("C")) &
                F.col("invoice_no").isNotNull() &
                F.col("stock_code").isNotNull() &
                F.col("quantity").isNotNull() &
                F.col("invoice_date").isNotNull() &
                F.col("unit_price").isNotNull() &
                F.col("customer_id").isNotNull() &
                F.col("country").isNotNull() &

            # Filter out invalid and test values
                (F.col("quantity") > 0) &
                (F.col("unit_price") >= 0) &
                (F.lower(F.trim(F.col("country"))) != "utopia")
            )

            # Drop duplicates
            .dropDuplicates(["customer_id", "invoice_no", "stock_code", "invoice_date", "quantity"])
            
            # Anonymized Customer ID
            .withColumn("customer_id_hash", F.sha2(F.concat(F.col("customer_id"), F.lit(SALT)), 256))
            
            # Calculate revenue
            .withColumn("revenue", F.round(F.col("quantity")* F.col("unit_price"), 2))
        
            # Add sale date and month
            .withColumn("sale_date", F.to_date(F.col("invoice_date")))
            .withColumn("sale_month", F.date_trunc("month", F.col("invoice_date")))

            # Select final columns
            .select(
                "invoice_no",
                "stock_code",
                "description",
                "quantity",
                "invoice_date",
                "sale_date",
                "sale_month",
                "unit_price",
                "customer_id_hash",
                "country",
                "revenue",
            )
        )

        # Write output
        cleaned_df.write.format("parquet").mode("overwrite").save(output_path)
        (
            cleaned_df.write.format("jdbc").mode("overwrite")
            .option("url", f"jdbc:postgresql://{postgres_host}:5432/{postgres_db}")
            .option("dbtable", "public.sales_clean")
            .option("user", postgres_user)
            .option("password", postgres_password)
            .option("driver", "org.postgresql.Driver")
            .save()
        )
        # Log
        row_count = cleaned_df.count()
        print(f"🚀 [transform] Transformed {row_count} rows into {output_path}")
    finally:
        spark.stop()

if __name__ == "__main__":
    main()