import os
from collections import defaultdict

import requests
import json
import time

AIRFLOW_API_URL = os.environ.get('AIRFLOW_API_URL')

AIRFLOW_API_TOKEN = os.environ.get("AIRFLOW_API_TOKEN")

HEADERS = {"Authorization": "Bearer " + AIRFLOW_API_TOKEN}


def list_dags():
    response = requests.get(f"{AIRFLOW_API_URL}/dags", headers=HEADERS)
    dags = [dag["dag_id"] for dag in response.json()['dags'] if "example_master_dag" != dag['dag_id']]
    return dags


def get_latest_dag_run_statuses(dags):
    dag_run_statuses = defaultdict(list)
    for dag_id in dags:
        response = requests.get(f"{AIRFLOW_API_URL}/dags/{dag_id}/dagRuns", headers=HEADERS)
        dag_runs = response.json()['dag_runs']
        if len(dag_runs) >= 7:
            dag_runs = dag_runs[-7:]
        else:
            dag_runs = dag_runs
        for dag_run in dag_runs:
            while dag_run["state"] == "running":
                # Wait for a certain period (e.g., 5 seconds) before retrying
                time.sleep(200)
                response = requests.get(f"{AIRFLOW_API_URL}/dags/{dag_id}/dagRuns", headers=HEADERS)
                dag_run = response.json()['dag_runs'][-1]

            dag_run_statuses[str(dag_id)].append(
                {
                    "status": dag_run["state"],
                    "execution_date": dag_run["execution_date"]
                }
            )
    return dag_run_statuses


if __name__ == "__main__":
    dags_list = list_dags()
    dag_run_statuses_map = get_latest_dag_run_statuses(dags_list)

    with open("dag_run_statuses.json", "w") as f:
        json.dump(dag_run_statuses_map, f)
