import subprocess
import pathlib

from aws_cdk import core
from aws_cdk import aws_s3
from aws_cdk import aws_lambda
from aws_cdk import aws_lambda_event_sources
from aws_cdk import aws_s3_notifications


class ImagePipelineProcessing(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str, processing_bucket_name, processing_bucket_upload_prefix, processing_bucket_output_prefix) -> None:
        super().__init__(scope, construct_id)

        processing_bucket = aws_s3.Bucket(self,
                                          'processing_bucket',
                                          bucket_name=processing_bucket_name,
                                          removal_policy=core.RemovalPolicy.DESTROY,
                                          cors=[aws_s3.CorsRule(
                                              allowed_headers=["*"],
                                              allowed_methods=[aws_s3.HttpMethods.PUT],
                                              allowed_origins=["*"])])

        # this lambda will process images once they arrive in s3
        lambda_name = 'image-pipeline-image-processor'
        current_path = str(pathlib.Path(__file__).parent.parent.absolute())
        print(current_path)
        commands = ("docker run --rm --entrypoint /bin/bash -v "
                    + current_path
                    + "/lambda_layers:/lambda_layers python:3.8 -c "
                    + "'pip3 install Pillow==8.1.0 -t /lambda_layers/python'")
        subprocess.run(commands, shell=True)
        lambda_layer = aws_lambda.LayerVersion(
            self,
            lambda_name+"-layer",
            compatible_runtimes=[aws_lambda.Runtime.PYTHON_3_8],
            code=aws_lambda.Code.asset("lambda_layers"))

        image_processing_lambda = aws_lambda.Function(
            self,
            lambda_name,
            function_name=lambda_name,
            runtime=aws_lambda.Runtime.PYTHON_3_8,
            code=aws_lambda.Code.asset('lambda_functions/image_processor'),
            handler='app.handler',
            layers=[lambda_layer],
            timeout=core.Duration.minutes(3),
            retry_attempts=0,
            environment={
                "OUTPUT_BUCKET": processing_bucket_name,
                "OUTPUT_PREFIX": processing_bucket_output_prefix
            }
        )
        # set up lambda to trigger from s3 upload
        lambda_notification = aws_s3_notifications.LambdaDestination(image_processing_lambda)
        processing_bucket.add_event_notification(
            aws_s3.EventType.OBJECT_CREATED,
            lambda_notification,
            aws_s3.NotificationKeyFilter(prefix=processing_bucket_upload_prefix))

        # will need to read the raw image and write processed images
        processing_bucket.grant_read_write(image_processing_lambda)

        # return this so the uploading stack can use them
        self.processing_bucket = processing_bucket
