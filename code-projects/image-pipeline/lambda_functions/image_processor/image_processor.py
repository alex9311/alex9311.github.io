import os
import ntpath
import uuid
import boto3
from PIL import Image

IMAGE_SIZES = [(16, 16), (32, 32), (512, 512)]


def insert_image(image_table, image_name, height, width, s3_key, s3_bucket):
    new_game_id = str(uuid.uuid1())
    new_image = {
        "id": new_game_id,
        "image_name": image_name,
        "height": height,
        "width": width,
        "s3_key": s3_key,
        "s3_bucket": s3_bucket
    }
    image_table.put_item(Item=new_image)


def handler(event, context):
    expected_env_vars = ["OUTPUT_PREFIX", "OUTPUT_BUCKET", "IMAGE_TABLE_NAME"]
    if not all(env_var_name in os.environ for env_var_name in expected_env_vars):
        raise ValueError('expected '+str(expected_env_vars)+' in environment')
    output_prefix = os.environ['OUTPUT_PREFIX']
    output_bucket = os.environ["OUTPUT_BUCKET"]
    image_table_name = os.environ['IMAGE_TABLE_NAME']

    ddb = boto3.resource('dynamodb')
    image_table = ddb.Table(image_table_name)

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
        insert_image(image_table,
                     image_name,
                     size[0],
                     size[1],
                     s3_output_key,
                     output_bucket)

    return True
