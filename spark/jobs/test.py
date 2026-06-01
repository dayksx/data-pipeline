from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("test").getOrCreate()

dataframe = spark.read.csv("data/retails.csv", header=True, inferSchema=True)

dataframe.show()