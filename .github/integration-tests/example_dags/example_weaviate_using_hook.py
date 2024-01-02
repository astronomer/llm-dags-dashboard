import json
from pathlib import Path

import pendulum
from airflow.decorators import dag, task, teardown
from airflow.providers.weaviate.hooks.weaviate import WeaviateHook


@dag(
    schedule=None,
    start_date=pendulum.datetime(2021, 1, 1, tz="UTC"),
    catchup=False,
    tags=["example", "weaviate"],
)
def example_weaviate_dag_using_hook():
    """Example Weaviate DAG demonstrating usage of the hook."""

    @task()
    def create_class_with_vectorizer():
        """
        Example task to create class with OpenAI Vectorizer responsible for vectorining data using Weaviate cluster.
        """
        weaviate_hook = WeaviateHook()
        class_obj = {
            "class": "QuestionWithOpenAIVectorizerUsingHook",
            "description": "Information from a Jeopardy! question",  # description of the class
            "properties": [
                {
                    "dataType": ["text"],
                    "description": "The question",
                    "name": "question",
                },
                {
                    "dataType": ["text"],
                    "description": "The answer",
                    "name": "answer",
                },
                {
                    "dataType": ["text"],
                    "description": "The category",
                    "name": "category",
                },
            ],
            "vectorizer": "text2vec-openai",
        }
        weaviate_hook.create_class(class_obj)

    @task()
    def create_class_without_vectorizer():
        """
        Example task to create class without any Vectorizer. You're expected to provide custom vectors for your data.
        """
        weaviate_hook = WeaviateHook()
        # Class definition object. Weaviate's autoschema feature will infer properties when importing.
        class_obj = {
            "class": "QuestionWithoutVectorizerUsingHook",
            "vectorizer": "none",
        }
        weaviate_hook.create_class(class_obj)

    @task(trigger_rule="all_done")
    def store_data_without_vectors_in_xcom():
        data = json.load(Path("./dags/jeopardy_data_without_vectors.json").open())
        return data

    @task(trigger_rule="all_done")
    def store_data_with_vectors_in_xcom():
        data = json.load(Path("./dags/jeopardy_data_with_vectors.json").open())
        return data

    @task(trigger_rule="all_done")
    def batch_data_without_vectors(data: list):
        weaviate_hook = WeaviateHook()
        weaviate_hook.batch_data("QuestionWithOpenAIVectorizerUsingHook", data)

    @task(trigger_rule="all_done")
    def batch_data_with_vectors(data: list):
        weaviate_hook = WeaviateHook()
        weaviate_hook.batch_data("QuestionWithoutVectorizerUsingHook", data)

    @teardown
    @task
    def delete_weaviate_class_Vector():
        """
        Example task to delete a weaviate class
        """
        weaviate_hook = WeaviateHook()
        # Class definition object. Weaviate's autoschema feature will infer properties when importing.

        weaviate_hook.delete_classes(["QuestionWithOpenAIVectorizerUsingHook"])

    @teardown
    @task
    def delete_weaviate_class_without_Vector():
        """
        Example task to delete a weaviate class
        """
        weaviate_hook = WeaviateHook()
        # Class definition object. Weaviate's autoschema feature will infer properties when importing.

        weaviate_hook.delete_classes(["QuestionWithoutVectorizerUsingHook"])

    data_with_vectors = store_data_with_vectors_in_xcom()
    (
        create_class_without_vectorizer()
        >> batch_data_with_vectors(data_with_vectors["return_value"])
        >> delete_weaviate_class_Vector()
    )

    data_without_vectors = store_data_without_vectors_in_xcom()
    (
        create_class_with_vectorizer()
        >> batch_data_without_vectors(data_without_vectors["return_value"])
        >> delete_weaviate_class_without_Vector()
    )


example_weaviate_dag_using_hook()
