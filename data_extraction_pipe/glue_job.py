import boto3
import config

from typing import Any


s3_script_path = "s3://sfeda-mlops-processed/etl_script_folder/etl_job.py"


class EtlJobClient:
    def __init__(self, glue_client: Any, name: str, s3_script_path: str) -> None:
        self.client = glue_client
        self.name = name
        self.s3_script_path = s3_script_path

    def create_etl_job(self) -> str:
        response = self.client.create_job(
            Name=self.name,
            Description="transformation of crawled data",
            Role=config.IAM_ROLE,
            ExecutionProperty={"MaxConcurrentRuns": 2},
            Command={"Name": "glueetl", "ScriptLocation": s3_script_path, "PythonVersion": "3"},
            MaxRetries=0,
            Timeout=1440,
            Tags=config.OWNERSHIP_TAG,
            NumberOfWorkers=5,
            WorkerType="Standard",
        )
        return response["Name"]

    def run_etl_job(self) -> str:
        response = self.client.start_job_run(JobName="string")
        return response["JobRunId"]

    def delete_etl_job(self) -> None:
        self.client.delete_job(JobName=self.name)


client = boto3.client("glue", region_name=config.REGION)
etl_job_client = EtlJobClient(client, "sfeda-mlops-etl-job", s3_script_path)
etl_job_client.create_etl_job()
etl_job_client.delete_etl_job()
