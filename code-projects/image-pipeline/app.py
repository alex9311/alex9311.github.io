#!/usr/bin/env python3
from aws_cdk import core

from image_pipeline.image_pipeline_processing import ImagePipelineProcessing
from image_pipeline.image_pipeline_upload import ImagePipelineUpload


app = core.App()
environment_name = app.node.try_get_context("ENVIRONMENT") or "dev"

environments = app.node.try_get_context("ENVIRONMENTS")
environment = environments.get(environment_name)
public_bucket_name = environment.get("public_bucket_name")
processing_bucket_name = environment.get("processing_bucket_name")
processing_bucket_upload_prefix = environment.get("processing_bucket_upload_prefix")
processing_bucket_output_prefix = environment.get("processing_bucket_output_prefix")


processing_stack = ImagePipelineProcessing(app, "image-pipeline-processing",
                                           processing_bucket_name=processing_bucket_name,
                                           processing_bucket_upload_prefix=processing_bucket_upload_prefix,
                                           processing_bucket_output_prefix=processing_bucket_output_prefix)

ImagePipelineUpload(app, "image-pipeline-upload",
                    public_bucket_name=public_bucket_name,
                    processing_bucket=processing_stack.processing_bucket,
                    processing_bucket_upload_prefix=processing_bucket_upload_prefix)


app.synth()
