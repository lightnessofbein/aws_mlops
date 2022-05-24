import boto3
import config

from typing import Any


class DataCatalogClient:
    def __init__(self, glue_client: Any, db_name: str) -> None:
        self.client = glue_client
        self.db_name = db_name

    def create_database(self) -> None:
        response = client.create_database(
            DatabaseInput={
                'Name': self.db_name,
                'Description': 'string',
                'LocationUri': 'string',
            }
        )

        return response['ResponseMetadata']['HTTPStatusCode']

    def delete_glue_database(self) -> None:
        self.client.delete_database(Name=self.db_name)


client = boto3.client('glue', region_name=config.REGION)
dbClient = DataCatalogClient(client, 'sfeda-mlops-db')
dbClient.create_database()

#dbClient.delete_glue_database()
