import json
from pathlib import Path

import pendulum
from airflow.decorators import dag, setup, task, teardown
from airflow.providers.weaviate.hooks.weaviate import WeaviateHook
from airflow.providers.weaviate.operators.weaviate import WeaviateIngestOperator

class_name = "Weaviate_with_vectorizer_example_class"


@dag(
    schedule=None,
    start_date=pendulum.datetime(2021, 1, 1, tz="UTC"),
    catchup=False,
    tags=["example", "weaviate"],
)
def example_weaviate_vectorizer_dag():
    """
    Example DAG which uses WeaviateIngestOperator to insert embeddings to Weaviate with vectorizer as text2vec-openai and then query to verify the response .
    """

    @setup
    @task
    def create_weaviate_class():
        """
        Example task to create class without any Vectorizer. You're expected to provide custom vectors for your data.
        """
        weaviate_hook = WeaviateHook()
        # Class definition object. Weaviate's autoschema feature will infer properties when importing.
        class_obj = {
            "class": class_name,
            "vectorizer": "text2vec-openai",
        }
        weaviate_hook.create_class(class_obj)

    @setup
    @task
    def get_data_to_ingest():
        data = json.load(Path("./dags/jeopardy_data_without_vectors.json").open())
        return data

    data_to_ingest = get_data_to_ingest()

    perform_ingestion = WeaviateIngestOperator(
        task_id="perform_ingestion",
        conn_id="weaviate_default",
        class_name=class_name,
        input_json=data_to_ingest["return_value"],
    )

    @task
    def query_weaviate():
        weaviate_hook = WeaviateHook()
        properties = ["question", "answer", "category"]
        response = weaviate_hook.query_without_vector(
            "biology", "Weaviate_with_vectorizer_example_class", *properties
        )
        assert "In 1953 Watson & Crick built a model" in response["data"]["Get"][class_name][0]["question"]

    @teardown
    @task
    def delete_weaviate_class():
        """
        Example task to delete a weaviate class
        """
        weaviate_hook = WeaviateHook()
        # Class definition object. Weaviate's autoschema feature will infer properties when importing.

        weaviate_hook.delete_classes([class_name])

    delete_weaviate_class = delete_weaviate_class()
    create_weaviate_class() >> perform_ingestion >> query_weaviate() >> delete_weaviate_class


example_weaviate_vectorizer_dag()
