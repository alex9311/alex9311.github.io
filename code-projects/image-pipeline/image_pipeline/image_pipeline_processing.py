from aws_cdk import core
from aws_cdk import aws_s3
from aws_cdk import aws_lambda
from aws_cdk import aws_apigateway


class ImagePipelineProcessing(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str, bucket) -> None:
        super().__init__(scope, construct_id)
