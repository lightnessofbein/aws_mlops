import boto3
import json


def lambda_handler(event, context):

    modifiedFiles = event["commits"][0]["modified"]
    # full path
    for filePath in modifiedFiles:
        # Extract folder name
        folderName = (filePath[:filePath.find("/")])
        break

    # start the pipeline
    if len(folderName) > 0:
        # Codepipeline name is foldername-job.
        # We can read the configuration from S3 as well.
        start_code_pipeline(folderName + '-job')

    return {
        'statusCode': 200,
        'body': json.dumps('Modified project in repo:' + folderName)
    }


def start_code_pipeline(pipelineName):
    client = codepipeline_client()
    client.start_pipeline_execution(name=pipelineName)
    return True


cpclient = None


def codepipeline_client():

    global cpclient
    if not cpclient:
        cpclient = boto3.client('codepipeline')
    return cpclient
