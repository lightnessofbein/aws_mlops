import boto3
import config

folder_name = 'lambdaGitWatcher'
lambda_name = f'{config.IAM_USERNAME}-{folder_name}'

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

