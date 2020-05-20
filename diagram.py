from diagrams import Cluster, Diagram
from diagrams.aws.iot import InternetOfThings, IotCore, IotEvents
from diagrams.aws.management import Cloudwatch
from diagrams.aws.compute import Lambda
from diagrams.aws.storage import S3
from diagrams.aws.database import Dynamodb
from diagrams.aws.integration import SQS, SNS
from diagrams.aws.ml import Rekognition

with Diagram("IOT Diagram", show=True, direction="TB"):

    _iotoutside = InternetOfThings("ESP-32 Board")

    with Cluster("AWS Serverless IOT"):

        _iotcore = IotCore("ESP-32 Iot Core")
        _iotevent = IotEvents("Event trigger SQS")
        _sqsesp32 = SQS("SQS Queue ESP32")
        _logsesp32 = Cloudwatch("Log Operations")
        _eventtriggeresp32 = Cloudwatch("Event Trigger to LAMBDA")
        _lambdaprocessimages = Lambda("Lambda process images")
        _imgrekog = Rekognition("Rekognition process")
        _tabledynamo = Dynamodb("Table history")
        _s3bucket = S3("S3 bucket images converted")
        _snstopico = SNS("Alert cat found")


    _iotoutside >> _iotcore >> _iotevent >> _sqsesp32
    _iotcore >> _logsesp32 
    _eventtriggeresp32 >> _lambdaprocessimages >> _sqsesp32
    _lambdaprocessimages >> _imgrekog
    _imgrekog >> _lambdaprocessimages
    _lambdaprocessimages >> _tabledynamo
    _lambdaprocessimages >> _s3bucket
    _lambdaprocessimages >> _snstopico
    _lambdaprocessimages >> _logsesp32



    