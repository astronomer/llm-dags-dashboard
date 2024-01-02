FROM quay.io/astronomer/astro-runtime:10.0.0-base
USER root
RUN apt update && apt install -y git openssh-client && rm -rf /var/lib/apt/lists/*
COPY example_dags/ ${AIRFLOW_HOME}/dags/
COPY dist  dist
RUN chmod 777 dist
RUN pip install --no-cache-dir dist/*.whl
RUN pip install apache-airflow-providers-slack
USER astro
