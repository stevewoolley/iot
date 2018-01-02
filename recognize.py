from __future__ import print_function
import boto3
import json
import io
import uuid
from PIL import Image
import PIL.Image

dynamodb = boto3.client('dynamodb')
s3 = boto3.client('s3')
rekognition = boto3.client('rekognition')

SNAPSHOTS = 'snapshots.snerted.com'
COLLECTION = 'snerted'
CONFIDENCE = 75
DDB_TABLE = 'faces'


def tagify(arr, field):
    o = []
    for i in arr:
        if field in i:
            o.append(i[field])
    return '+'.join(o)


def lambda_handler(event, context):
    print("Received event: {}".format(json.dumps(event)))

    if 'Records' in event:
        for record in event['Records']:
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            tags = {}

            # detect objects
            result = rekognition.detect_labels(
                Image={'S3Object': {'Bucket': bucket, 'Name': key}}, MinConfidence=CONFIDENCE)
            if "Labels" in result:
                tags['recognize'] = tagify(result['Labels'], 'Name')

            # detect faces
            response = rekognition.detect_faces(Image={'S3Object': {'Bucket': bucket, 'Name': key}})
            all_faces = response['FaceDetails']
            download_path = '/tmp/{}{}'.format(uuid.uuid4(), key)
            s3.download_file(bucket, key, download_path)
            image = Image.open(download_path)
            stream = io.BytesIO()
            image.save(stream, format="JPEG")
            image_width = image.size[0]
            image_height = image.size[1]
            print("Main image width: {} height: {}".format(image_width, image_height))
            names = []
            print("All faces: {}".format(all_faces))
            for face in all_faces:
                box = face['BoundingBox']

                x1 = int(box['Left'] * image_width) * 0.9
                y1 = int(box['Top'] * image_height) * 0.9
                x2 = int(box['Left'] * image_width + box['Width'] * image_width) * 1.10
                y2 = int(box['Top'] * image_height + box['Height'] * image_height) * 1.10
                image_crop = image.crop((x1, y1, x2, y2))

                stream = io.BytesIO()
                image_crop.save(stream, format="JPEG")
                image_crop_binary = stream.getvalue()
                print("Cropped image: {},{} - {},{}".format(x1, y1, x2, y2))
                # Submit individually cropped image to Amazon Rekognition
                try:
                    response = rekognition.search_faces_by_image(
                        CollectionId=COLLECTION,
                        Image={'Bytes': image_crop_binary}
                    )
                    if len(response['FaceMatches']) > 0:
                        match = response['FaceMatches'][0]
                        face = dynamodb.get_item(
                            TableName=DDB_TABLE,
                            Key={'id': {'S': match['Face']['FaceId']}}
                        )
                        if 'Item' in face:
                            names.append(face['Item']['name']['S'])
                        else:
                            names.append('Unknown')
                except Exception as e:
                    print("search_faces_by_image failed: {}".format(e.message))
            if len(names) > 0:
                tags['identities'] = '+'.join(names)

            # add the tags
            existing_tags = s3.get_object_tagging(Bucket=bucket, Key=key)['TagSet']
            if tags is not None:
                for k, v in tags.items():
                    existing_tags.append({'Key': k.strip(), 'Value': v.strip()})
                s3.put_object_tagging(Bucket=bucket, Key=key, Tagging={'TagSet': existing_tags})
