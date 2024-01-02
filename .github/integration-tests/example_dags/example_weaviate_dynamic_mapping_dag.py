import json
from pathlib import Path

import pendulum
from airflow.decorators import dag, setup, task, teardown
from airflow.providers.weaviate.hooks.weaviate import WeaviateHook
from airflow.providers.weaviate.operators.weaviate import WeaviateIngestOperator


@dag(
    schedule=None,
    start_date=pendulum.datetime(2021, 1, 1, tz="UTC"),
    catchup=False,
    tags=["example", "weaviate"],
)
def example_weaviate_dynamic_mapping_dag():
    """
    Example DAG which uses WeaviateIngestOperator to insert embeddings to Weaviate using dynamic mapping"""

    @setup
    @task
    def create_weaviate_class(data):
        """
        Example task to create class without any Vectorizer. You're expected to provide custom vectors for your data.
        """
        weaviate_hook = WeaviateHook()
        # Class definition object. Weaviate's autoschema feature will infer properties when importing.
        class_obj = {
            "class": data[0],
            "vectorizer": data[1],
        }
        weaviate_hook.create_class(class_obj)

    @setup
    @task
    def get_data_to_ingest():
        file1 = json.load(Path("./dags/jeopardy_data_with_vectors.json").open())
        file2 = json.load(Path("./dags/jeopardy_data_without_vectors.json").open())
        return [file1, file2]

    get_data_to_ingest = get_data_to_ingest()

    perform_ingestion = WeaviateIngestOperator.partial(
        task_id="perform_ingestion",
        conn_id="weaviate_default",
    ).expand(
        class_name=["example1", "example2"],
        input_json=get_data_to_ingest["return_value"],
    )

    @teardown
    @task
    def delete_weaviate_class(class_name):
        """
        Example task to delete a weaviate class
        """
        weaviate_hook = WeaviateHook()
        # Class definition object. Weaviate's autoschema feature will infer properties when importing.

        weaviate_hook.delete_classes([class_name])

    (
        create_weaviate_class.expand(data=[["example1", "none"], ["example2", "text2vec-openai"]])
        >> perform_ingestion
        >> delete_weaviate_class.expand(class_name=["example1", "example2"])
    )


example_weaviate_dynamic_mapping_dag()
