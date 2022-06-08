import json
from boto3 import client


def lambda_handler(event, context):

    body_str = event.get("body", "{}")
    body_obj = json.loads(body_str)
    folderName = []

    commits = body_obj['commits']
    for commit in commits:
        folderName += [filePath[:filePath.find("/")] for filePath in commit['modified'] if 'lambda' in filePath]

    # start the pipeline
    if len(folderName) > 0:
        for singleFolderName in folderName:
            # Codepipeline name is user-foldername-job.
            start_code_pipeline(f'sfeda-{singleFolderName}')

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
