#!/usr/bin/env python3
from aws_cdk import core

from image_pipeline.image_pipeline_processing import ImagePipelineProcessing
from image_pipeline.image_pipeline_upload_handler import ImagePipelineUploadHandler
from image_pipeline.image_pipeline_upload_site import ImagePipelineUploadSite


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

upload_handler_stack = ImagePipelineUploadHandler(app, "image-pipeline-upload-handler",
                                                  processing_bucket=processing_stack.processing_bucket,
                                                  processing_bucket_upload_prefix=processing_bucket_upload_prefix)

ImagePipelineUploadSite(app, "image-pipeline-upload-site",
                        public_bucket_name=public_bucket_name,
                        api=upload_handler_stack.api)


app.synth()
