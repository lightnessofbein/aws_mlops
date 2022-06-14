IAM_USERNAME = 'sfeda'
REGION: str = 'us-west-1'
IAM_ROLE: str = f'service-role/AWSGlueServiceRole-{IAM_USERNAME}-mlops-retrain'
OWNERSHIP_TAG: dict[str, str] = {'owner': IAM_USERNAME}


GITHUB_OAUTH_TOKEN: str = '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'  # TODO: add auth token securily
