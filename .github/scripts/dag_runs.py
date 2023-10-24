import os
from collections import defaultdict

import requests
import json

AIRFLOW_API_URL = os.environ.get('AIRFLOW_API_URL')
AIRFLOW_API_URL = "https://org-airflow-team-org.astronomer.run/d5omliyj/api/v1"

AIRFLOW_API_TOKEN = os.environ.get("AIRFLOW_API_TOKEN")
AIRFLOW_API_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcGlUb2tlbklkIjoiY2xvNG4zeDZhMDBnOTAxbnU3ZG5reDI2NSIsImF1ZCI6ImFzdHJvbm9tZXItZWUiLCJpYXQiOjE2OTgxNzA5MDAsImlzQXN0cm9ub21lckdlbmVyYXRlZCI6dHJ1ZSwiaXNzIjoiaHR0cHM6Ly9hcGkuYXN0cm9ub21lci5pbyIsImtpZCI6ImNsZjhtazJrajAwNzUwMWw2bjc4OTgyaHIiLCJwZXJtaXNzaW9ucyI6WyJhcGlUb2tlbklkOmNsbzRuM3g2YTAwZzkwMW51N2Rua3gyNjUiLCJ3b3Jrc3BhY2VJZDpjbGplOGdwaDAwMXZ5MDFtbWpzeXhsMzh1Iiwib3JnYW5pemF0aW9uSWQ6Y2xqZThnbXc2MDFzbTAxbXU0cjJvOHk3eiIsIm9yZ1Nob3J0TmFtZTpvcmctYWlyZmxvdy10ZWFtLW9yZyJdLCJzY29wZSI6ImFwaVRva2VuSWQ6Y2xvNG4zeDZhMDBnOTAxbnU3ZG5reDI2NSB3b3Jrc3BhY2VJZDpjbGplOGdwaDAwMXZ5MDFtbWpzeXhsMzh1IG9yZ2FuaXphdGlvbklkOmNsamU4Z213NjAxc20wMW11NHIybzh5N3ogb3JnU2hvcnROYW1lOm9yZy1haXJmbG93LXRlYW0tb3JnIiwic3ViIjoiY2wyNHM2dXAwMTE4MTE4MDdmdjJvcXR2MyIsInZlcnNpb24iOiJjbG80bjN4NmEwMGc4MDFudXF6bndiNGxuIn0.Mzs7etxA77_PpEa1Npc5oplw2BJpXcosxtL9wtzj184O7gVIKrxGi9NEB2RQGHqhjohCpoI-oCNYv-Fi-NSB8JQ5cUdymL4KBr2eI59o2nSD87hnjh_7BQSQgoqaWUH-i9N20V8DWXRF4LUeVlGQ2oqz3fZXD1MH1-gmRLS2G_Qt01A97SXoB_x9E5FrAQFMYeukJ0jURisDWfw5gK0kYXs0FHjGPYN_9YrJYX8McsauGeEzRSD4BGoYR6Q3SrTJb7JQXTxdKLG0wSJkLUuE9Sann39JFzUCZXz_rBuVwYc2o3zqgreAc8Ie9nHTFtFxWysxuliYO0_I3EHFckz2cA"

HEADERS = {"Authorization": "Bearer " + AIRFLOW_API_TOKEN}


def list_dags():
    response = requests.get(f"{AIRFLOW_API_URL}/dags", headers=HEADERS)
    dags = [dag["dag_id"] for dag in response.json()['dags']]
    return dags


def get_latest_dag_run_statuses(dags):
    dag_run_statuses = defaultdict(list)
    for dag_id in dags:
        response = requests.get(f"{AIRFLOW_API_URL}/dags/{dag_id}/dagRuns?limit=7", headers=HEADERS)
        dag_runs = response.json()['dag_runs']
        for dag_run in dag_runs:
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
