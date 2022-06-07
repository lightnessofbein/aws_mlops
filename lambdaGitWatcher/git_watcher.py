import json
from boto3 import client


def lambda_handler(event, context):

    modifiedFiles = event["commits"][0]["modified"]
    # full path
    for filePath in modifiedFiles:
        # Extract folder name
        folderName = (filePath[:filePath.find("/")])
        break

    # start the pipeline
    if len(folderName) > 0:
        # Codepipeline name is user-foldername-job.
        start_code_pipeline(f'sfeda-{folderName}-job')

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
        cpclient = client('codepipeline')
    return cpclient
