import os
import events
import s3proc
import docproc
import syncproc
import asyncproc
import jobresultsproc
import helper
import uuid
import json
import datastore

# Update variables below according to your infrastructure
# You only need this if you want to test lambda code locally
syncQueueUrl = "https://sqs.us-east-2.amazonaws.com/929835491811/OmnomStack-SyncJobs0FE0C444-83PKXDIXAVWC"
asyncQueueUrl = "https://sqs.us-east-2.amazonaws.com/929835491811/OmnomStack-AsyncJobsE9347181-642VRQ5FQV7H"
bucketName = "omnomstack-documentsbucket9ec9deb9-jqz6fjwc1vrk"

documentsTableName = "OmnomStack-DocumentsTable7E808EE5-DJRGTG03Y6SX"
outputTableName = "OmnomStack-OutputForms2663C270-WDRUEQ36JC4G"

snsTopic = "arn:aws:sns:us-east-2:929835491811:OmnomStack-OmnomJobCompletion0BCED563-1ARMR5LFTDLWJ"
snsRole = "arn:aws:iam::929835491811:role/OmnomStack-OmnomServiceRoleAD67DD40-161K2D092XW1C"

s3Image = "employmentapp.png"
s3Pdf = "pdfdoc.pdf"
s3LargePdf = "pdfdoc.pdf"

def clearEnvironment():
    os.environ['SYNC_QUEUE_URL'] = ""
    os.environ['ASYNC_QUEUE_URL'] = ""
    os.environ['DOCUMENTS_TABLE'] = ""
    os.environ['OUTPUT_TABLE'] = ""
    os.environ['SNS_TOPIC_ARN'] = ""
    os.environ['SNS_ROLE_ARN'] = ""

def createImageDocument(documentCount=1):
    
    event = events.s3Event(bucketName, s3Image)
    
    clearEnvironment()
    os.environ['DOCUMENTS_TABLE'] = documentsTableName
    os.environ['OUTPUT_TABLE'] = outputTableName

    i = 0
    while(i < documentCount):    
        s3proc.lambda_handler(event, None)
        i += 1

def processImageDocument(documentId=str(uuid.uuid1()), documentCount = 1):
    
    clearEnvironment()
    os.environ['SYNC_QUEUE_URL'] = syncQueueUrl
    os.environ['ASYNC_QUEUE_URL'] = asyncQueueUrl

    i = 0
    while(i < documentCount):    
        event = events.documentEvent(documentId, bucketName, s3Image)
        docproc.lambda_handler(event, None)
        i += 1

def createPdfDocument(documentCount=1):
    
    event = events.s3Event(bucketName, s3Pdf)
    
    clearEnvironment()
    os.environ['DOCUMENTS_TABLE'] = documentsTableName
    os.environ['OUTPUT_TABLE'] = outputTableName

    i = 0
    while(i < documentCount):    
        s3proc.lambda_handler(event, None)
        i += 1

def processPdfDocument(documentId=str(uuid.uuid1()), documentCount = 1):
    
    clearEnvironment()
    os.environ['SYNC_QUEUE_URL'] = syncQueueUrl
    os.environ['ASYNC_QUEUE_URL'] = asyncQueueUrl

    i = 0
    while(i < documentCount):    
        event = events.documentEvent(documentId, bucketName, s3Pdf)
        docproc.lambda_handler(event, None)
        i += 1

def processSyncJob(documentId="e5ea2b4a-7162-11e9-958a-c4b301c10017"):

    event = events.syncQueueDocument(documentId, bucketName, s3Image)

    clearEnvironment()
    os.environ['OUTPUT_TABLE'] = outputTableName
    os.environ['DOCUMENTS_TABLE'] = documentsTableName

    syncproc.lambda_handler(event, None)

def processAsyncJobs():

    event = {}

    clearEnvironment()
    os.environ['SNS_TOPIC_ARN'] = snsTopic
    os.environ['SNS_ROLE_ARN'] = snsRole
    os.environ['ASYNC_QUEUE_URL'] = asyncQueueUrl

    asyncproc.lambda_handler(event, None)

def processJobResults():
    
    event = events.jobResultsEvent("2e8462d30cb50e66e67d2709b3cce90f01118594016c0df328534185000ae32f", 
                            "12917fdc-6357-11e9-b05d-42237b865595",
                            "SUCCESS",
                            "['Text', 'FORMS', 'TABLES']",
                            bucketName, s3Pdf)

    clearEnvironment()    
    os.environ['OUTPUT_TABLE'] = outputTableName
    os.environ['DOCUMENTS_TABLE'] = documentsTableName

    jobresultsproc.lambda_handler(event, None)

def dataStore_getDocuments():
        
        #Document
        print("*******************")
        dstore = datastore.DocumentStore(documentsTableName, outputTableName)
        docs = dstore.getDocuments()
        print(docs)
        print("------------")
        while("nextToken" in docs):
            print(docs["nextToken"])
            docs = dstore.getDocuments(docs["nextToken"])
            print(docs)
        print("------------")

#Sync Pipeline
#createImageDocument()
#processImageDocument("822927b4-7798-11e9-8495-4a0007597ab0")
#processSyncJob("822927b4-7798-11e9-8495-4a0007597ab0")

#Async Pipeline
createPdfDocument(1)
processPdfDocument()
processAsyncJobs()
processJobResults()
