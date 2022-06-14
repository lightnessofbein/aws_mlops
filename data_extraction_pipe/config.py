IAM_USERNAME = 'sfeda'
REGION: str = 'us-west-1'
IAM_ROLE: str = f'service-role/AWSGlueServiceRole-{IAM_USERNAME}-mlops-retrain'
OWNERSHIP_TAG: dict[str, str] = {'owner': IAM_USERNAME}


GITHUB_OAUTH_TOKEN: str = ' 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'  # TODO: add auth token securily
