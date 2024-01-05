"""Master Dag to run all the example dags."""
import logging
import os
import time
from datetime import datetime
from typing import Any, List

from airflow import DAG
from airflow.models import DagRun
from airflow.models.baseoperator import chain
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator
from airflow.utils.session import create_session

SLACK_CHANNEL = os.getenv("SLACK_CHANNEL", "#llm-alerts")
SLACK_WEBHOOK_CONN = os.getenv("SLACK_WEBHOOK_CONN", "http_slack")
SLACK_USERNAME = os.getenv("SLACK_USERNAME", "airflow_app")
MASTER_DAG_SCHEDULE = os.getenv("MASTER_DAG_SCHEDULE", None)
IS_RUNTIME_RELEASE = bool(os.getenv("IS_RUNTIME_RELEASE", False))


def get_report(dag_run_ids: List[str], **context: Any) -> None:
    """Fetch dags run details and generate report."""
    with create_session() as session:
        last_dags_runs: List[DagRun] = session.query(DagRun).filter(DagRun.run_id.in_(dag_run_ids)).all()
        message_list: List[str] = []

        airflow_version = context["ti"].xcom_pull(task_ids="get_airflow_version")
        airflow_executor = context["ti"].xcom_pull(task_ids="get_airflow_executor")
        astro_cloud_provider = context["ti"].xcom_pull(task_ids="get_astro_cloud_provider")

        report_details = [
            f"*{header}:* `{value}`\n"
            for header, value in [
                ("Runtime version", os.getenv("ASTRONOMER_RUNTIME_VERSION", "N/A")),
                ("Python version", os.getenv("PYTHON_VERSION", "N/A")),
                ("Airflow version", airflow_version),
                ("Executor", airflow_executor),
                ("LLM-providers-version", "Providers installed for Apache Airflow main sources"),
                ("Cloud provider", astro_cloud_provider),
            ]
        ]

        report_details.insert(0, "Results generated for:\n\n")
        report_details.append("\n")  # Adding an additional newline at the end

        cloud_ui_deployment_link = os.getenv("AIRFLOW__ASTRONOMER__CLOUD_UI_URL", None)
        master_dag_deployment_link = f"{os.environ['AIRFLOW__WEBSERVER__BASE_URL']}/dags/example_master_dag/grid?search=example_master_dag"
        deployment_message = f"\n <{master_dag_deployment_link}|Link> to the master DAG for the above run on <{cloud_ui_deployment_link}|Astro Cloud deployment> \n"

        dag_count, failed_dag_count = 0, 0
        for dr in last_dags_runs:
            dr_status = f" *{dr.dag_id} : {dr.get_state()}* \n"
            dag_count += 1
            failed_tasks = []
            for ti in dr.get_task_instances():
                task_code = ":black_circle: "
                if not ((ti.task_id == "end") or (ti.task_id == "get_report")):
                    if ti.state == "success":
                        continue
                    elif ti.state == "failed":
                        task_code = ":red_circle: "
                        failed_tasks.append(f"{task_code} {ti.task_id} : {ti.state} \n")
                    elif ti.state == "upstream_failed":
                        task_code = ":large_orange_circle: "
                        failed_tasks.append(f"{task_code} {ti.task_id} : {ti.state} \n")
                    else:
                        failed_tasks.append(f"{task_code} {ti.task_id} : {ti.state} \n")
            if failed_tasks:
                message_list.append(dr_status)
                message_list.extend(failed_tasks)
                failed_dag_count += 1

        output_list = [
            f"*Total DAGS*: {dag_count} \n",
            f"*Success DAGS*: {dag_count-failed_dag_count} :green_apple: \n",
            f"*Failed DAGS*: {failed_dag_count} :apple: \n \n",
        ]
        output_list = report_details + output_list
        if failed_dag_count > 0:
            output_list.append("*Failure Details:* \n")
            output_list.extend(message_list)
        dag_run = context["dag_run"]
        task_instances = dag_run.get_task_instances()

        task_failure_message_list: List[str] = [
            f":red_circle: {ti.task_id} \n" for ti in task_instances if ti.state == "failed"
        ]

        if task_failure_message_list:
            output_list.append(
                "\nSome of Master DAG tasks failed, please check with deployment link below \n"
            )
            output_list.extend(task_failure_message_list)
        output_list.append(deployment_message)
        logging.info("%s", "".join(output_list))
        # Send dag run report on Slack
        try:
            SlackWebhookOperator(
                task_id="slack_alert",
                slack_webhook_conn_id=SLACK_WEBHOOK_CONN,
                message="".join(output_list),
                channel=SLACK_CHANNEL,
                username=SLACK_USERNAME,
            ).execute(context=None)
        except Exception as exception:
            logging.exception("Error occur while sending slack alert.")
            raise exception


def prepare_dag_dependency(task_info, execution_time):
    """Prepare list of TriggerDagRunOperator task and dags run ids for dags of same providers."""
    _dag_run_ids = []
    _task_list = []
    for _example_dag in task_info:
        _task_id = list(_example_dag.keys())[0]

        _run_id = f"{_task_id}_{_example_dag.get(_task_id)}_" + execution_time
        _dag_run_ids.append(_run_id)
        _task_list.append(
            TriggerDagRunOperator(
                task_id=_task_id,
                trigger_dag_id=_example_dag.get(_task_id),
                trigger_run_id=_run_id,
                wait_for_completion=True,
                reset_dag_run=True,
                execution_date=execution_time,
                allowed_states=["success", "failed"],
                trigger_rule="all_done",
            )
        )
    return _task_list, _dag_run_ids


with DAG(
    dag_id="example_master_dag",
    schedule=MASTER_DAG_SCHEDULE,
    start_date=datetime(2022, 1, 1),
    catchup=False,
    tags=["master_dag"],
) as dag:
    # Sleep for 30 seconds so that all the example dag will be available before master dag trigger them
    start = PythonOperator(
        task_id="start",
        python_callable=lambda: time.sleep(30),
    )

    list_installed_pip_packages = BashOperator(
        task_id="list_installed_pip_packages", bash_command="pip freeze"
    )

    get_airflow_version = BashOperator(
        task_id="get_airflow_version", bash_command="airflow version", do_xcom_push=True
    )

    get_airflow_executor = BashOperator(
        task_id="get_airflow_executor",
        bash_command="airflow config get-value core executor",
        do_xcom_push=True,
    )

    get_astro_cloud_provider = BashOperator(
        task_id="get_astro_cloud_provider",
        bash_command=(
            "[[ $AIRFLOW__LOGGING__REMOTE_LOG_CONN_ID == *azure* ]] && echo 'azure' ||"
            "([[ $AIRFLOW__LOGGING__REMOTE_LOG_CONN_ID == *s3* ]] && echo 'aws' ||"
            "([[ $AIRFLOW__LOGGING__REMOTE_LOG_CONN_ID == *gcs* ]] && echo 'gcs' ||"
            "echo 'unknown'))"
        ),
        do_xcom_push=True,
    )

    dag_run_ids = []

    weaviate_dags_info = [
        {"weaviate_using_hook": "example_weaviate_dag_using_hook"},
        {"weaviate_using_operator": "example_weaviate_using_operator"},
        {"weaviate_vectorizer_dag": "example_weaviate_vectorizer_dag"},
        {"weaviate_without_vectorizer_dag": "example_weaviate_without_vectorizer_dag"},
        {"weaviate_dynamic_mapping_dag": "example_weaviate_dynamic_mapping_dag"},
    ]
    weaviate_tasks, ids = prepare_dag_dependency(weaviate_dags_info, "{{ ts }}")
    dag_run_ids.extend(ids)
    chain(*weaviate_tasks)

    pinecone_dags_info = [
        {"pinecone_cohere": "example_pinecone_cohere"},
        {"pinecone_openai": "example_pinecone_openai"},
    ]
    pinecone_tasks, ids = prepare_dag_dependency(pinecone_dags_info, "{{ ts }}")
    dag_run_ids.extend(ids)
    chain(*pinecone_tasks)

    openai_dag_info = [
        {"openai_dag": "example_openai_dag"},
        {"openai_weaviate": "example_weaviate_openai"},
    ]

    openai_tasks, ids = prepare_dag_dependency(openai_dag_info, "{{ ts }}")
    dag_run_ids.extend(ids)
    chain(*openai_tasks)

    cohere_dags_info = [
        {"cohere_dag": "example_cohere_embedding"},
        {"cohere_weaviate_dag": "example_weaviate_cohere"},
    ]
    cohere_tasks, ids = prepare_dag_dependency(cohere_dags_info, "{{ ts }}")
    dag_run_ids.extend(ids)
    chain(*cohere_tasks)

    pgvector_dag_info = [
        {"openai_pgvector_dag": "example_openai_pgvector_dag"},
        {"pgvector_dag": "example_pgvector_dag"},
    ]

    pgvector_tasks, ids = prepare_dag_dependency(pgvector_dag_info, "{{ ts }}")
    dag_run_ids.extend(ids)
    chain(*pgvector_tasks)

    report = PythonOperator(
        task_id="get_report",
        python_callable=get_report,
        op_kwargs={"dag_run_ids": dag_run_ids},
        trigger_rule="all_done",
        provide_context=True,
    )

    end = EmptyOperator(
        task_id="end",
        trigger_rule="all_success",
    )

    start >> [
        list_installed_pip_packages,
        get_airflow_version,
        get_airflow_executor,
        get_astro_cloud_provider,
        weaviate_tasks[0],
        pinecone_tasks[0],
        openai_tasks[0],
        cohere_tasks[0],
        pgvector_tasks[0],
    ]

    last_task = [
        list_installed_pip_packages,
        get_airflow_version,
        get_airflow_executor,
        get_astro_cloud_provider,
        weaviate_tasks[-1],
        pinecone_tasks[-1],
        openai_tasks[-1],
        cohere_tasks[-1],
        pgvector_tasks[-1],
    ]

    last_task >> report >> end
