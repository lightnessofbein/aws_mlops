import boto3
from time import gmtime, strftime
from os import path

region = boto3.Session().region_name
# TODO: remove hardcode
username = 'sfeda'
smclient = boto3.Session().client('sagemaker')
role = 'arn:aws:iam::508741970469:role/service-role/sfeda-lambda-role-0za8fvd6'

bucket_path = 's3://sfeda-mlops-processed'
prefix = "processed_data"

TRAIN_DATA_PREFIX = '/train-data'
TEST_DATA_PREFIX = '/val-data'

container = "746614075791.dkr.ecr.us-west-1.amazonaws.com/sagemaker-xgboost:1.3-1"


def lambda_handler(event, context):
    tuning_job_config = \
        {
            "ParameterRanges": {
                "CategoricalParameterRanges": [],
                "ContinuousParameterRanges": [
                    {
                        "MaxValue": "1",
                        "MinValue": "0",
                        "Name": "eta"
                    },
                    {
                        "MaxValue": "2",
                        "MinValue": "0",
                        "Name": "alpha"
                    },
                    {
                        "MaxValue": "10",
                        "MinValue": "1",
                        "Name": "min_child_weight"
                    }
                ],
                "IntegerParameterRanges": [
                    {
                        "MaxValue": "20",
                        "MinValue": "10",
                        "Name": "max_depth"
                    }
                ]
            },
            "ResourceLimits": {
                "MaxNumberOfTrainingJobs": 5,
                "MaxParallelTrainingJobs": 5
            },
            "Strategy": "Bayesian",
            "HyperParameterTuningJobObjective": {
                "MetricName": "validation:mae",
                "Type": "Minimize"
            }
        }

    training_job_definition = \
        {
            "AlgorithmSpecification": {
                "TrainingImage": container,
                "TrainingInputMode": "File"
            },
            "RoleArn": role,
            "OutputDataConfig": {
                "S3OutputPath": path.join(bucket_path, prefix, "xgboost")
            },
            "ResourceConfig": {
                "InstanceCount": 2,
                "InstanceType": "ml.m5.2xlarge",
                "VolumeSizeInGB": 32
            },
            "StaticHyperParameters": {
                "objective": "reg:linear",
                "num_round": "20",
                "subsample": "0.7",
                "eval_metric": "mae"
            },
            "StoppingCondition": {
                "MaxRuntimeInSeconds": 86400
            },
            "InputDataConfig": [
                {
                    "ChannelName": "train",
                    "DataSource": {
                        "S3DataSource": {
                            "S3DataType": "S3Prefix",
                            # TODO: remove hardcode
                            "S3Uri": "s3://sfeda-mlops-processed/processed_data/train-data/run-datasink_train-4-part-r-00000",
                            "S3DataDistributionType": "FullyReplicated"
                            
                        }
                    },
                    "ContentType": "text/csv",
                    "CompressionType": "None"
                },
                {
                    "ChannelName": "validation",
                    "DataSource": {
                        "S3DataSource": {
                            "S3DataType": "S3Prefix",
                            # TODO: remove hardcode
                            "S3Uri": "s3://sfeda-mlops-processed/processed_data/train-data/run-datasink_train-4-part-r-00000",
                            "S3DataDistributionType": "FullyReplicated"
                        }
                    },
                    "ContentType": "text/csv",
                    "CompressionType": "None"
                }
            ]
        }
    # TODO: remove hardcode and add yaml config with user name
    tuning_job_name = f'{username}-hptuning-{strftime("%Y%m%d%H%M%S", gmtime())}'

    event["container"] = container
    event["stage"] = "Training"
    event["status"] = "InProgress"
    event['HyperParameterTuningJobName'] = tuning_job_name

    print(event)
    smclient.create_hyper_parameter_tuning_job(HyperParameterTuningJobName=tuning_job_name,
                                               HyperParameterTuningJobConfig=tuning_job_config,
                                               TrainingJobDefinition=training_job_definition)

    return event
