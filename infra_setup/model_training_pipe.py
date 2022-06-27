import boto3
import requests
import time


training_lambda_url = 'https://sfptrhrga7pjgvv73opdkpdc3i0stbis.lambda-url.us-west-1.on.aws/'
deploy_lambda_url = ''
finish_status_list = ['InProgress', 'Stopping']


if __name__ == '__main__':
    sage_client = boto3.Session().client('sagemaker')
    response = requests.post(training_lambda_url).json()

    current_status = 'InProgress'
    while current_status in finish_status_list:
        time.sleep(60*10)
        current_status = sage_client.describe_training_job(TrainingJobStatus=response['name'])

    deploy_response = requests.post(deploy_lambda_url, data={})
