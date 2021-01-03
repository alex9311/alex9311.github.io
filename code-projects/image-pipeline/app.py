#!/usr/bin/env python3
from aws_cdk import core

from image_pipeline.image_pipeline_bucket import ImagePipelineBucket
from image_pipeline.image_pipeline_upload import ImagePipelineUpload
from image_pipeline.image_pipeline_processing import ImagePipelineProcessing


app = core.App()
environment_name = app.node.try_get_context("ENVIRONMENT") or "dev"

bucket_stack = ImagePipelineBucket(app, "image-pipeline-bucket", environment_name)
ImagePipelineUpload(app,
                    "image-pipeline-upload",
                    public_bucket=bucket_stack.public_bucket,
                    processing_bucket=bucket_stack.processing_bucket)

ImagePipelineProcessing(app, "image-pipeline-processing", bucket=bucket_stack.processing_bucket)


app.synth()

