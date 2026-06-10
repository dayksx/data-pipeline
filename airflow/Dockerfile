FROM apache/airflow:2.9.2-python3.11

USER root

RUN apt-get update && apt-get install -y openjdk-17-jdk

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="$JAVA_HOME/bin:$PATH"

USER airflow

RUN pip install --no-cache-dir \
    apache-airflow-providers-apache-spark==4.8.1 \
    pyspark==3.5.1 \
    psycopg[binary]>=3.1 \
    pydantic-settings>=2.2 \
    python-dotenv \
    langchain-openai>=0.2