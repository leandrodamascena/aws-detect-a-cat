"""
This is a personal script to play with tech and AWS resources
You can modify this whatever you want, be free
"""

import base64
import boto3
import json
import uuid
from datetime import datetime


SQS_QUEUE_URL = "" #Queue URL
S3_BUCKET_NAME = "" #Bucket name
SNS_TOPIC_ARN = "" #ARN topic to subscribe a message in SNS
DYNAMODB_TABLE = "" #Dynamodb table name
REGION_NAME = "" #Region
CONFIDENCE = 50 #Confidence must be 50 or higher 



""" Dynamodb functions """
def insertRegistry(imageId, found, s3Prefix):

    dynamodb = boto3.resource('dynamodb',region_name=REGION_NAME)
    table = dynamodb.Table(DYNAMODB_TABLE)

    table.put_item(
            Item={
                'imageId': imageId,
                'found': found,
                's3Prefix': s3Prefix,
                'timestamp': str(datetime.utcnow().isoformat())
            }
        )

def checkTableExists():
    """ 
    Check if table exists and create a table if not exist
    You can remove this function if you know how to create table before to run this 
    """
    dynamodb = boto3.client('dynamodb',region_name=REGION_NAME)
    try:
        response = dynamodb.describe_table(TableName=DYNAMODB_TABLE)
    except dynamodb.exceptions.ResourceNotFoundException:
        table = dynamodb.create_table(AttributeDefinitions=[ 
            { 
                'AttributeName': 'imageId', 
                'AttributeType': 'S', 
            }, 
            { 
                'AttributeName': 'found',
                'AttributeType': 'S',
            },
            ],
            KeySchema=[
                {
                    'AttributeName': 'imageId',
                    'KeyType': 'HASH',\
                },
                {
                    'AttributeName': 'found',
                    'KeyType': 'RANGE',\
                },
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5,
            },
            TableName=DYNAMODB_TABLE)

        """ Wait until table creation done """
        dynamodb.get_waiter('table_exists').wait(TableName=DYNAMODB_TABLE,WaiterConfig={
            'Delay': 10,
            'MaxAttempts': 30
        })
        print("Created table")
        pass

""" S3 functions """
def uploadToS3(imageFile, s3bucket, s3Prefix):

    s3 = boto3.client('s3',region_name=REGION_NAME)
    s3.upload_file(imageFile, s3bucket, s3Prefix, ExtraArgs={'ACL': 'public-read'})

""" SNS functions """
def subscribeTopic(imagemUrl):

    sns = boto3.client('sns',region_name=REGION_NAME)

    imagemUrl = "https://{0}.s3.amazonaws.com/{1}".format(S3_BUCKET_NAME, imagemUrl)
    response = sns.publish(
        TopicArn=SNS_TOPIC_ARN,    
        Message='A cat was found in bedroom. See the picture in follow link: {0}'.format(imagemUrl)
    )


""" Instance all resources to use """
sqs = boto3.client('sqs',region_name=REGION_NAME)
rekognition=boto3.client('rekognition',region_name=REGION_NAME)

def lambda_handler(event, context):

    """ Check if DynamoDB Table exists... The first time execution script will be slow """
    checkTableExists()
    
    """ Consumes queue from SQS to check if new messages are available """
    messages = sqs.receive_message(QueueUrl=SQS_QUEUE_URL,MaxNumberOfMessages=1)
    
    if "Messages" in messages:
    
        now = datetime.now()
    
        """ Found a message, let start to test """
        messageid = messages['Messages'][0]['ReceiptHandle']
        messagebody = base64.b64decode(json.loads(messages['Messages'][0]['Body'])["picture"])
    
        """ Saving a img into /tmp dict... Lambda allows to use tmp directory to save temp files """
        imageId = str(uuid.uuid4())
        imgtempname = "/tmp/{0}.{1}".format(imageId,"jpg")
        with open(imgtempname,"wb") as f:
            f.write(messagebody)
    
        """ Starting rekognition script """
        print("Starting rekognition script...")
        with open(imgtempname,"rb") as image:
            objects = rekognition.detect_labels(Image={'Bytes': image.read()})
    
        try:
            datenow = now.strftime("%m-%d-%Y")
            s3Prefix = "notfound/"+datenow+"/"
            found = "False"
            for labels in objects['Labels']:
                """ Check if has a label called "cat" and confidence equals/higher than global variable CONFIDENCE"""
                if labels['Name'].lower() == 'animal' and labels['Confidence'] >= CONFIDENCE:
                    found = "True"
                    s3Prefix = "found/"+datenow+"/"
                    print("A cat has been found...")
                    
            """ Inserting data in dynamodb to keep history """
            print("Saving metadata into dynamodb...")
            insertRegistry(imageId=imageId, found=found, s3Prefix=s3Prefix)
    
            """ Saving image in S3 bucket """
            print("Saving image into s3...")
            uploadToS3(imageFile=imgtempname,s3bucket=S3_BUCKET_NAME,s3Prefix=s3Prefix+imgtempname.replace("/tmp/",""))
    
            """ If found, subscribe a topic to alert """
            if found == "True":
                print("Subscribing a SNS topic to alert that a cat has been found...")
                subscribeTopic(s3Prefix+imgtempname.replace("/tmp/",""))
    
            """ Deleting SQS message """
            print("Deleting SQS message...")
            sqs.delete_message(
                QueueUrl=SQS_QUEUE_URL,
                ReceiptHandle=messageid
            )
               
        except Exception as e:
            print(str(e))
    
    else:
        print("There is no MESSAGES to process...")
