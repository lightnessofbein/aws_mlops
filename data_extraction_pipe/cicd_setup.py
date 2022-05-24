import boto3
import config
import requests


gateway_name = f'{config.IAM_USERNAME}-testing'
lambda_name = 'sfeda-gitwatcher'
# gitwatcher_lambda_uri = 'arn:aws:lambda:us-west-1:508741970469:function:sfeda-gitwatcher'
# what we need
# arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:123456789012:function:HelloWorld/invocations
# 1:123456789012:function:HelloWorld is partial arn of lambda
# arn:aws:apigateway:{region}:{subdomain.service|service}:path|action/{service_api} - template for integration URI
#gitwatcher_lambda_uri = 'arn:aws:lambda:us-west-1:508741970469:function:sfeda-gitwatcher'

gitwatcher_lambda_uri = 'arn:aws:lambda:us-west-1:508741970469:function:sfeda-test'
integration_lambda_uri = f'arn:aws:apigateway:{config.REGION}:lambda:path/' + \
                         f'2015-03-31/functions/{gitwatcher_lambda_uri}/invocations'


gitwatcher_dict = {}
# using v1 and not v2 bec of REST available on v1, http and websocket are available on v2
client = boto3.client('apigateway', region_name=config.REGION)
response = client.create_rest_api(name=gateway_name,
                                  endpointConfiguration={
                                      'types': ['REGIONAL']},
                                  disableExecuteApiEndpoint=False,
                                  tags=config.OWNERSHIP_TAG)
gitwatcher_dict['restApiId'] = response['id']
gitwatcher_dict['resourceId'] = client.get_resources(
    restApiId=response['id'])['items'][0]['id']

client.put_method(restApiId=gitwatcher_dict['restApiId'],
                  resourceId=gitwatcher_dict['resourceId'],
                  httpMethod='POST',
                  authorizationType='NONE')

client.put_integration(restApiId=gitwatcher_dict['restApiId'],
                       resourceId=gitwatcher_dict['resourceId'],
                       httpMethod='POST',
                       type='AWS_PROXY',
                       integrationHttpMethod='POST',
                       uri=integration_lambda_uri,
                       )

# add lambda permission to be invoked by api
client = boto3.client('lambda')
response = client.add_permission(
    FunctionName=lambda_name,
    StatementId=f'{gateway_name}-{gitwatcher_dict["restApiId"]}-invokepermission',
    Action='lambda:InvokeFunction',
    Principal='apigateway.amazonaws.com',
    SourceArn=f'arn:aws:execute-api:{config.REGION}:508741970469:{gitwatcher_dict["restApiId"]}/*/POST/'
)

restapi_http = f"https://{gitwatcher_dict['restApiId']}.execute-api.{config.REGION}.amazonaws.com/{stage_name}/"

# creating webhook to the restapi just created
hook = {u'name': u'web', u'active': True, u'config': {u'url': u'http://my/payload/destination'}}
p = requests.post(
    'https://api.github.com/repos/lightnessofbein/aws_mlops/hooks', 
    json=hook, headers={'Authorization': f'token {config.GITHUB_OAUTH_TOKEN}'})

# [2] setting up CodePipeline


# [2.1] setting up CodeBuild
client = boto3.client('codebuild', region_name=config.REGION)
client.create_project(
    name=lambda_name,
    description='kill me',
    source={
        'type': 'CODEPIPELINE',
        # empty string forces codebuild to use buildspec.yaml from source root
        'buildspec': '',
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
                                     'namespace': 'BuildVariables'}]},

                    {'name': 'Deploy',
                     'actions': [{'name': 'Deploy',
                                  'actionTypeId': {'category': 'Deploy',
                                                   'owner': 'AWS',
                                                   'provider': 'CodeDeploy',
                                                   'version': '1'},
                                  'runOrder': 1,
                                  'configuration': {'ApplicationName': lambda_name,
                                                    'DeploymentGroupName': lambda_name},
                                  'outputArtifacts': [],
                                  'inputArtifacts': [{'name': 'BuildArtifact'}],
                                  'region': config.REGION,
                                  'namespace': 'DeployVariables'}]}],
                'version': 1},
    tags=[
        {
            'key': 'owner',
            'value': config.OWNERSHIP_TAG['owner']
        },
    ]
)
