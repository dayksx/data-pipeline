import os
from pyspark.sql import SparkSession

BASE = os.getenv("PIPELINE_ROOT", "/opt/pipeline")
input_path = f"{BASE}/data/retails.csv"

spark = SparkSession.builder.appName("test").getOrCreate()

dataframe = spark.read.csv(input_path, header=True, inferSchema=True)

dataframe.show()