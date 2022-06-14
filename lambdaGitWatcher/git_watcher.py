import json
from typing import Any, Dict
from boto3 import client


PIPECLIENT = client('codepipeline')


def lambda_handler(event: Dict[str, Any], context):

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
            PIPECLIENT.start_pipeline_execution(name=f'sfeda-{singleFolderName}')

    return {
        'statusCode': 200,
        'body': json.dumps('Modified project in repo:' + '; '.join(folderName))
    }
