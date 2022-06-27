import boto3
import config
#import requests


gateway_name = f'{config.IAM_USERNAME}-testing'
folder_name = 'lambdaGitWatcher'
lambda_name = f'{config.IAM_USERNAME}-{folder_name}'
# gitwatcher_lambda_uri = 'arn:aws:lambda:us-west-1:508741970469:function:sfeda-gitwatcher'
# what we need
# arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:123456789012:function:HelloWorld/invocations
# 1:123456789012:function:HelloWorld is partial arn of lambda
# arn:aws:apigateway:{region}:{subdomain.service|service}:path|action/{service_api} - template for integration URI
# gitwatcher_lambda_uri = 'arn:aws:lambda:us-west-1:508741970469:function:sfeda-gitwatcher'

# creating webhook to the restapi just created
# hook = {u'name': u'web', u'active': True, u'config': {u'url': u'http://my/payload/destination'}}
# p = requests.post(
#    'https://api.github.com/repos/lightnessofbein/aws_mlops/hooks', 
#    json=hook, headers={'Authorization': f'token {config.GITHUB_OAUTH_TOKEN}'})

# [2] setting up CodePipeline
# [2.1] setting up CodeBuild
client = boto3.client('codebuild', region_name=config.REGION)
client.create_project(
    name=lambda_name,
    description='',
    source={
        'type': 'CODEPIPELINE',
        # empty string forces codebuild to use buildspec.yaml from source root
        'buildspec': f'{folder_name}/buildspec.yaml',
    },
    artifacts={'type': 'CODEPIPELINE'},
    # TODO: remove hardcode
    serviceRole='arn:aws:iam::508741970469:role/service-role/sfeda-mlops',

    cache={
        'type': 'NO_CACHE',
    },
    environment={
        'type': 'LINUX_CONTAINER',
        'image': 'aws/codebuild/standard:4.0',
        'imagePullCredentialsType': 'CODEBUILD',
        'computeType': 'BUILD_GENERAL1_SMALL',
    },
    tags=[
        {
            'key': 'owner',
            'value': config.OWNERSHIP_TAG['owner']
        },
    ]
)

# [2.2] setting up CodePipeline itself
client = boto3.client('codepipeline', region_name=config.REGION)
response = client.create_pipeline(
    pipeline={
        'name': lambda_name,
        # TODO: add ARN generations and remove hardcode
        'roleArn': 'arn:aws:iam::508741970469:role/service-role/AWSCodePipelineServiceRole-us-west-1-sfeda-mlops-test',
        'artifactStore': {
            'type': 'S3',
            'location': 'sfeda-mlops-processed',  # TODO: change hardcoded s3 location.
        },
        'stages': [
            {
                'name': 'Source',
                'actions': [
                    {
                        'name': 'Source',
                        'actionTypeId': {
                            'category': 'Source',  # |'Build'|'Deploy'|'Test'|'Invoke'|'Approval',
                            'owner': 'ThirdParty',
                            'provider': 'GitHub',
                            'version': '1'
                        },
                        'runOrder': 1,
                        'configuration': {
                            'Owner': 'lightnessofbein',
                            'Branch': 'main',
                            'OAuthToken': config.GITHUB_OAUTH_TOKEN,
                            'PollForSourceChanges': 'false',
                            # todo: set it up as a parameter
                            'Repo': 'aws_mlops'
                        },
                        'outputArtifacts': [
                            {
                                'name': 'SourceArtifact'
                            },
                        ],
                        # 'roleArn': 'string',
                        'region': config.REGION,
                        'namespace': 'SourceVariables'}]},
                    {'name': 'Build',
                        'actions': [{'name': 'Build',
                                     'actionTypeId': {'category': 'Build',
                                                      'owner': 'AWS',
                                                      'provider': 'CodeBuild',
                                                      'version': '1'},
                                     'runOrder': 1,
                                     'configuration': {'ProjectName': lambda_name},
                                     'outputArtifacts': [{'name': 'BuildArtifact'}],
                                     'inputArtifacts': [{'name': 'SourceArtifact'}],
                                     'region': config.REGION,
                                     'namespace': 'BuildVariables'}]},],
                'version': 1},
    tags=[
        {
            'key': 'owner',
            'value': config.OWNERSHIP_TAG['owner']
        },
    ]
)

