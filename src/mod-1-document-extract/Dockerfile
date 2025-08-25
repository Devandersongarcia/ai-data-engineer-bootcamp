FROM astrocrpublic.azurecr.io/runtime:3.0-1

USER root

RUN apt-get update && apt-get install -y \
    postgresql-client \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

USER astro

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY config /usr/local/airflow/config

COPY include/sql /usr/local/airflow/include/sql