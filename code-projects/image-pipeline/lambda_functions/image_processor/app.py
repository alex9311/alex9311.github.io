import os
import ntpath

import boto3
from PIL import Image

IMAGE_SIZES = [(16, 16), (32, 32), (512, 512)]


def handler(event, context):
    output_prefix = os.environ['OUTPUT_PREFIX']
    output_bucket = os.environ["OUTPUT_BUCKET"]

    s3_resource = boto3.resource('s3')
    s3_client = boto3.client('s3')

    s3_data = event["Records"][0]["s3"]
    image_bucket_name = s3_data["bucket"]["name"]
    image_prefix = s3_data["object"]["key"]
    image_name = os.path.splitext(ntpath.basename(image_prefix))[0]

    local_filename = "/tmp/"+image_name+".jpg"
    s3_client.download_file(image_bucket_name, image_prefix, local_filename)

    for size in IMAGE_SIZES:
        local_filename_resized = (image_name+"_"
                                  + str(size[0])+"x"+str(size[1])
                                  + ".jpg")
        img = Image.open(local_filename)
        img = img.resize(size, Image.ANTIALIAS)
        img.save("/tmp/"+local_filename_resized)
        s3_output_key = output_prefix+"/"+local_filename_resized
        s3_resource.Bucket(output_bucket).upload_file(
            "/tmp/"+local_filename_resized,
            s3_output_key)

    return True
