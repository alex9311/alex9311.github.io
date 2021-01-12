from aws_cdk import core
from aws_cdk import aws_s3
from aws_cdk import aws_s3_deployment
from aws_cdk import aws_lambda
from aws_cdk import aws_apigateway

from string import Template


class ImagePipelineUploadSite(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str, public_bucket, api_url) -> None:
        super().__init__(scope, construct_id)

        print("got api_url: "+api_url)
        static_template_file_name = 'static_upload_site/index-template.html'

        with open(static_template_file_name, 'r') as f:
            src = Template(f.read())
            prepared_site_content = src.substitute({"api_url": api_url})

        with open('static_upload_site/index.html', 'w') as f:
            f.write(prepared_site_content)

        # static site hosted on s3 allowing uploads
        static_upload_site = aws_s3_deployment.BucketDeployment(
            self,
            "deployStaticWebsite",
            sources=[aws_s3_deployment.Source.asset("static_upload_site")],
            destination_bucket=public_bucket
        )
