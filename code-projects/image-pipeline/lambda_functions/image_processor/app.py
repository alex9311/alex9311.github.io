import os
import boto3


def handler(event, context):
    print("called lambda")
    print(str(event))
    s3_data = event["Records"][0]["s3"]
    print(str(s3_data))
    image_bucket_name = s3_data["bucket"]["name"]
    image_path = s3_data["object"]["key"]
    print(str({"image_bucket_name": image_bucket_name, "image_path": image_path}))
    return True
