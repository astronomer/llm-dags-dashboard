import os
from datetime import datetime

from airflow import DAG
from airflow.providers.pinecone.operators.pinecone import PineconeIngestOperator

index_name = os.getenv("INDEX_NAME", "example-pinecone-index")
namespace = os.getenv("NAMESPACE", "example-pinecone-index")


with DAG(
    "example_pinecone_ingest",
    schedule_interval=None,
    start_date=datetime(2023, 1, 1),
    catchup=False,
) as dag:
    # [START howto_operator_pinecone_ingest]
    PineconeIngestOperator(
        task_id="pinecone_vector_ingest",
        index_name=index_name,
        input_vectors=[
            ("id1", [1.0, 2.0, 3.0], {"key": "value"}),
            ("id2", [1.0, 2.0, 3.0]),
        ],
        namespace=namespace,
        batch_size=1,
    )
    # [END howto_operator_pinecone_ingest]
