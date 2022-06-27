from typing import Any
import boto3

import config


class CrawlerClient:
    def __init__(self, glue_client: Any, name: str) -> None:
        self.client = glue_client
        self.name = name

    def create_glue_crawler(self) -> None:
        response = self.client.create_crawler(
            Name=self.name,
            Role=config.IAM_ROLE,
            DatabaseName='sfeda-mlops-database',
            Targets={
                'S3Targets': [{'Path': 's3://sfeda-mlops-raw',
                               'Exclusions': ['logs/**', '*.ipynb']}]
            },
            SchemaChangePolicy={
                'UpdateBehavior': 'UPDATE_IN_DATABASE',
                'DeleteBehavior': 'DEPRECATE_IN_DATABASE'
            },
            RecrawlPolicy={
                'RecrawlBehavior': 'CRAWL_EVERYTHING'
            },
            Tags=config.OWNERSHIP_TAG
        )

        return response['ResponseMetadata']['HTTPStatusCode']

    def delete_glue_crawler(self) -> None:
        self.client.delete_crawler(Name=self.name)

    def run_glue_crawler(self) -> None:
        self.client.start_crawler(Name=self.name)


client = boto3.client('glue', region_name=config.REGION)
crawlerClient = CrawlerClient(client, 'sfeda-mlops-retrain-crawler')
crawlerClient.create_glue_crawler()
#crawlerClient.run_glue_crawler()
crawlerClient.delete_glue_crawler()
