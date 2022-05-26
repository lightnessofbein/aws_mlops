import boto3
import json
from os import path

sagemaker = boto3.client('sagemaker')
s3 = boto3.resource('s3')
EXECUTION_ROLE = 'arn:aws:iam::508741970469:role/service-role/sfeda-lambda-role-0za8fvd6'
INSTANCE_TYPE = 'ml.m5.2xlarge'
model_package_group_name = 'sfeda-model-package'
endpoint = 'sfeda-deployed'


DEPLOY = False
APPROVAL_METRIC_VALUE = 0.9
MODEL_PERFORMANCE_STORAGE = 'sfeda-mlops-processed'


def lambda_handler(event, context):
    # container = event['container']
    container = "746614075791.dkr.ecr.us-west-1.amazonaws.com/sagemaker-xgboost:1.3-1"

    best_training_job = event['best_training_job']

    # model_data_url = event['model_data_url']
    model_data_url = f'"s3://sfeda-mlops-processed/processed_data/xgboost/{best_training_job}/output/model.tar.gz"'

    # model_package_group_input_dict = {
    #     "ModelPackageGroupName": model_package_group_name,
    #     "ModelPackageGroupDescription": "Sample model package group"
    # }

    # sagemaker.create_model_package_group(**model_package_group_input_dict)

    print("Additional step - register model to model group")
    register_model_response = register_model(
        container, model_data_url, best_training_job)

    print("Save results of model (tunning job) to S3")
    training_job_description = sagemaker.describe_training_job(
        TrainingJobName=best_training_job)
    objective_metric_value = [element for element in training_job_description['FinalMetricDataList']
                              if element['MetricName'] == 'ObjectiveMetric'][0]['Value']
    s3object = s3.Object(MODEL_PERFORMANCE_STORAGE, path.join('model_reports', best_training_job) + '.json')
    resp = s3object.put(
        Body=(bytes(json.dumps(training_job_description, default=str).encode('UTF-8'))))

    print("Check if new model is better than current one and update its status in model registry")
    if objective_metric_value < APPROVAL_METRIC_VALUE:
        DEPLOY = True
        model_package_update_input_dict = {
            "ModelPackageArn": register_model_response['ModelPackageArn'],
            "ModelApprovalStatus": "Approved"}
        model_package_update_response = sagemaker.update_model_package(
            **model_package_update_input_dict)
    else:
        DEPLOY = False
        model_package_update_input_dict = {
            "ModelPackageArn": register_model_response['ModelPackageArn'],
            "ModelApprovalStatus": "Rejected"}
        model_package_update_response = sagemaker.update_model_package(
            **model_package_update_input_dict)

    print("Deploy model")
    if DEPLOY:
        print('Creating model resource from training artifact...')
        create_model(best_training_job, container, model_data_url)
        print('Creating endpoint configuration...')
        create_endpoint_config(best_training_job)
        print(
            'There is no existing endpoint for this model. Creating new model endpoint...')
        create_endpoint(endpoint, best_training_job)
        event['endpoint'] = endpoint
        event['stage'] = 'Deployment'
        event['status'] = 'Creating'
        event['message'] = 'Started deploying model "{}" to endpoint "{}"'.format(
            best_training_job, endpoint)
    else:
        event['endpoint'] = endpoint
        event['stage'] = 'Deployment'
        event['status'] = 'Not deployed'
        event['message'] = 'Model not deployed due to low metric value'
    return event


def register_model(container, model_data_url, best_training_job):

    modelpackage_inference_specification = {

        "InferenceSpecification": {
            "Containers": [
                {
                    "Image": container,
                }
            ],
            "SupportedContentTypes": ["text/csv"],
            "SupportedResponseMIMETypes": ["text/csv"], }}

    # Specify the model data
    modelpackage_inference_specification["InferenceSpecification"]["Containers"][0]["ModelDataUrl"] = model_data_url

    create_model_package_input_dict = {
        "ModelPackageGroupName": model_package_group_name,
        "ModelPackageDescription": best_training_job,
        "ModelApprovalStatus": "PendingManualApproval"}
    create_model_package_input_dict.update(
        modelpackage_inference_specification)
    create_mode_package_response = sagemaker.create_model_package(
        **create_model_package_input_dict)
    return create_mode_package_response


def create_model(name, container, model_data_url):
    """ Create SageMaker model.
    Args:
        name (string): Name to label model with
        container (string): Registry path of the Docker image that contains the model algorithm
        model_data_url (string): URL of the model artifacts created during training to download to container
    Returns:
        (None)
    """
    try:
        sagemaker.create_model(
            ModelName=name,
            PrimaryContainer={
                'Image': container,
                'ModelDataUrl': model_data_url
            },
            ExecutionRoleArn=EXECUTION_ROLE
        )
    except Exception as e:
        print(e)
        print('Unable to create model.')
        raise(e)


def create_endpoint_config(name):
    """ Create SageMaker endpoint configuration.
    Args:
        name (string): Name to label endpoint configuration with.
    Returns:
        (None)
    """
    try:
        sagemaker.create_endpoint_config(
            EndpointConfigName=name,
            ProductionVariants=[
                {
                    'VariantName': 'prod',
                    'ModelName': name,
                    'InitialInstanceCount': 1,
                    'InstanceType': INSTANCE_TYPE
                }
            ]
        )
    except Exception as e:
        print(e)
        print('Unable to create endpoint configuration.')
        raise(e)


def create_endpoint(endpoint_name, config_name):
    """ Create SageMaker endpoint with input endpoint configuration.
    Args:
        endpoint_name (string): Name of endpoint to create.
        config_name (string): Name of endpoint configuration to create endpoint with.
    Returns:
        (None)
    """
    try:
        sagemaker.create_endpoint(
            EndpointName=endpoint_name,
            EndpointConfigName=config_name
        )
    except Exception as e:
        print(e)
        print('Unable to create endpoint.')
        raise(e)
