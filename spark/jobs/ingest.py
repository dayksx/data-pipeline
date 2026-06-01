import os
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType

BASE = os.getenv("PIPELINE_ROOT", "/opt/pipeline")
input_path = f"{BASE}/data/retails.csv"
output_path = f"{BASE}/data/bronze/retails_raw"

def main() -> None:
    spark = SparkSession.builder.appName("ingest").config("spark.sql.session.timeZone", "UTC").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    try:
        # Read input file
        raw_df = spark.read.csv(input_path, header=True, sep=",", inferSchema=True)

        # Normalize string columns
        normalized_df = raw_df
        for column in raw_df.columns:
            if isinstance(raw_df.schema[column].dataType, StringType):
                normalized_df = normalized_df.withColumn(column, F.trim(column))

        # Add ingestion timestamp
        normalized_df = normalized_df.withColumn("ingested_at", F.current_timestamp())

        # Add source file
        normalized_df = normalized_df.withColumn("source_file", F.lit("retails.csv"))

        # Store in Parquet
        normalized_df.write.format("parquet").mode("overwrite").save(output_path)
    
        # Log
        row_count = normalized_df.count()
        print(f"🚀 [ingest] Ingested {row_count} rows into {output_path}")
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
