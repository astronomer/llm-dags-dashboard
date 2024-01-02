import pendulum
from airflow.decorators import dag, task
from airflow.providers.openai.hooks.openai import OpenAIHook
from airflow.providers.openai.operators.openai import OpenAIEmbeddingOperator


def input_text_callable(
    input_arg1: str,
    input_arg2: str,
    input_kwarg1: str = "default_kwarg1_value",
    input_kwarg2: str = "default_kwarg1_value",
):
    text = " ".join([input_arg1, input_arg2, input_kwarg1, input_kwarg2])
    return text


@dag(
    schedule=None,
    start_date=pendulum.datetime(2021, 1, 1, tz="UTC"),
    catchup=False,
    tags=["example", "openai"],
)
def example_openai_dag():
    """
    ### TaskFlow API Tutorial Documentation
    This is a simple data pipeline example which demonstrates the use of
    the TaskFlow API using three simple tasks for Extract, Transform, and Load.
    Documentation that goes along with the Airflow TaskFlow API tutorial is
    located
    [here](https://airflow.apache.org/docs/apache-airflow/stable/tutorial_taskflow_api.html)
    """

    @task()
    def create_embeddings_using_hook():
        """
        #### Extract task
        A simple Extract task to get data ready for the rest of the data
        pipeline. In this case, getting data is simulated by reading from a
        hardcoded JSON string.
        """
        openai_hook = OpenAIHook()
        embeddings = openai_hook.create_embeddings("hello how are you?")
        return embeddings

    @task(multiple_outputs=True)
    def task_to_store_input_text_in_xcom():
        return {"input_text": "Hello how are you?"}

    xcom_text = task_to_store_input_text_in_xcom()

    # [START howto_operator_openai_embedding]
    OpenAIEmbeddingOperator(
        task_id="embedding_using_xcom_data",
        conn_id="openai_default",
        input_text=xcom_text["input_text"],
        model="text-embedding-ada-002",
    )

    # [END howto_operator_openai_embedding]

    create_embeddings_using_hook()


example_openai_dag()