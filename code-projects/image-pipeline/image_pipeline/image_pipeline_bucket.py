from aws_cdk import core
from aws_cdk import aws_s3
from aws_cdk import aws_apigateway


class ImagePipelineBucket(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str, environment_name) -> None:
        super().__init__(scope, construct_id)

        environments = self.node.try_get_context("ENVIRONMENTS")
        environment = environments.get(environment_name)
        processing_bucket_name = environment.get("processing_bucket_name")
        public_bucket_name = environment.get("public_bucket_name")

        processing_bucket = aws_s3.Bucket(self,
                                          'processing_bucket',
                                          bucket_name=processing_bucket_name,
                                          removal_policy=core.RemovalPolicy.DESTROY,
                                          cors=[aws_s3.CorsRule(
                                              allowed_headers=["*"],
                                              allowed_methods=[aws_s3.HttpMethods.PUT],
                                              allowed_origins=["*"])])

        public_bucket = aws_s3.Bucket(self,
                                      'public_bucket',
                                      bucket_name=public_bucket_name,
                                      public_read_access=True,
                                      removal_policy=core.RemovalPolicy.DESTROY,
                                      website_index_document='index.html')

        self.processing_bucket = processing_bucket
        self.public_bucket = public_bucket
