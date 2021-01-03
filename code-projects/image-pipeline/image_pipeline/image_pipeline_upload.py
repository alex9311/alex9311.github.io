from aws_cdk import core
from aws_cdk import aws_s3_deployment
from aws_cdk import aws_lambda
from aws_cdk import aws_apigateway


class ImagePipelineUpload(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str, public_bucket, processing_bucket) -> None:
        super().__init__(scope, construct_id)

        # static site hosted on s3 allowing uploads
        static_upload_site = aws_s3_deployment.BucketDeployment(
            self,
            "deployStaticWebsite",
            sources=[aws_s3_deployment.Source.asset("static_upload_site")],
            destination_bucket=public_bucket
        )

        # lambda to act as upload API handler
        lambda_name = 'image-pipeline-s3-url-generator'
        s3_url_generator_lambda = aws_lambda.Function(
            self,
            lambda_name,
            function_name=lambda_name,
            runtime=aws_lambda.Runtime.NODEJS_12_X,
            code=aws_lambda.Code.asset('lambda_functions/get_signed_s3_url'),
            handler='app.handler',
            environment={'UploadBucket': processing_bucket.bucket_name},
            timeout=core.Duration.minutes(3)
        )
        # write access allows the lambda to generate signed urls
        processing_bucket.grant_write(s3_url_generator_lambda)

        # rest api endpoint to pass requests to lambda
        base_api = aws_apigateway.RestApi(self, 'ImageUpload',
                                          rest_api_name='ImageUpload')
        # we'll send uploads to the `image` prefix, CORS must be allowed
        image_entity = base_api.root.add_resource(
            'images',
            default_cors_preflight_options=aws_apigateway.CorsOptions(
                allow_origins=aws_apigateway.Cors.ALL_ORIGINS)
        )

        # hooks the endpoint up to the lambda above
        image_entity_lambda_integration = aws_apigateway.LambdaIntegration(
            s3_url_generator_lambda,
            proxy=False,
            integration_responses=[{
                'statusCode': '200',
                'responseParameters': {
                    'method.response.header.Access-Control-Allow-Origin': "'*'",
                }
            }])

        # GET will be used to get presigned url
        image_entity.add_method(
            'GET',
            image_entity_lambda_integration,
            method_responses=[{
                'statusCode': '200',
                'responseParameters': {
                    'method.response.header.Access-Control-Allow-Origin': True,
                }
            }])
