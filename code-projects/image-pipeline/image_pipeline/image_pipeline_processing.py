import subprocess
import pathlib

from aws_cdk import core
from aws_cdk import aws_s3
from aws_cdk import aws_lambda
from aws_cdk import aws_lambda_event_sources
from aws_cdk import aws_s3_notifications
from aws_cdk import aws_lambda_python
from aws_cdk import aws_dynamodb


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
        images_table_name = "images"
        ddb_images_table = aws_dynamodb.Table(
            self, "ddb_images_table",
            table_name=images_table_name,
            partition_key={
                "name": "id",
                "type": aws_dynamodb.AttributeType.STRING
            },
            removal_policy=core.RemovalPolicy.DESTROY  # NOT recommended for production code
        )

        # this lambda will process images once they arrive in s3
        lambda_name = 'image-pipeline-image-processor'
        image_processing_lambda = aws_lambda.Function(
            self,
            lambda_name,
            function_name=lambda_name,
            runtime=aws_lambda.Runtime.PYTHON_3_8,
            code=aws_lambda.Code.asset('lambda_functions/image_processor'),
            handler='image_processor.handler',
            layers=[aws_lambda_python.PythonLayerVersion(
                self,
                "lambda_layers",
                entry="lambda_layer",
                compatible_runtimes=[aws_lambda.Runtime.PYTHON_3_8]
            )],

            timeout=core.Duration.minutes(3),
            retry_attempts=0,
            environment={
                "OUTPUT_BUCKET": processing_bucket_name,
                "OUTPUT_PREFIX": processing_bucket_output_prefix,
                "IMAGE_TABLE_NAME": images_table_name
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
        ddb_images_table.grant_read_write_data(image_processing_lambda)

        # return this so the uploading stack can use them
        self.processing_bucket = processing_bucket
