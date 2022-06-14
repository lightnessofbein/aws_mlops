# import statements go here
import json
from typing import Any


# NAME OF THE FUNCTION IN AWS LAMBDA; by default, the name is "lambda_handler" or "my_handler" in the documentation
# this must be the name of your function as defined in AWS Lambda.
# This will be the function that AWS Lambda calls.
def my_serverless_function(event: Any, context: Any) -> dict[str, Any]:
    # some example list
    my_list: list[int] = []
    # ...do something to the list
    my_list = [1, 2, 3, 5, 8]
    # IMPORTANT: format list to be in an acceptable format for lambda
    json_mylist = json.dumps(my_list, separators=(',', ':'))

    # IMPORTANT: json format for making the results accessible through the API Gateway
    response = {
        "statusCode": 200,
        "body": json_mylist
    }

    # this returns some python list
    return response

#what