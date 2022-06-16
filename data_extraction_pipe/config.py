import os 
from dotenv import load_dotenv


load_dotenv()

IAM_USERNAME = 'sfeda'
REGION: str = 'us-west-1'
IAM_ROLE: str = f'service-role/AWSGlueServiceRole-{IAM_USERNAME}-mlops-retrain'
OWNERSHIP_TAG: dict[str, str] = {'owner': IAM_USERNAME}


GITHUB_OATH_TOKEN: str = os.environ.get('GITHUB_OATH_TOKEN', '')
