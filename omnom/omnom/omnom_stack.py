import aws_cdk.core as cdk
import aws_cdk.aws_sns as sns
import aws_cdk.aws_sns_subscriptions as sns_subscriptions
import aws_cdk.aws_iam as iam
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_dynamodb as dynamodb
import aws_cdk.aws_sqs as sqs

class OmnomStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

        # **********SNS Topics**********
        jobCompletionTopic = sns.Topic(self, 'Omnom-JobCompletion')


        # **********IAM Roles******************************
        textractServiceRole = iam.Role(self, 'OmnomServiceRole', assumed_by=iam.ServicePrincipal('textract.amazonaws.com'))
        textractServiceRole.add_to_policy(iam.PolicyStatement(
            effect = iam.Effect.ALLOW,
            resources = [jobCompletionTopic.topic_arn],
            actions = ["sns:Publish"]))

        # **********S3 Batch Operations Role******************************
        s3BatchOperationsRole = iam.Role(self, 'S3BatchOperationsRole', assumed_by=iam.ServicePrincipal('batchoperations.s3.amazonaws.com'))


        # **********S3 Bucket******************************
        # S3 bucket for input documents and output
        contentBucket = s3.Bucket(self, 'DocumentsBucket', versioned= False, auto_delete_objects = True, removal_policy = cdk.RemovalPolicy.DESTROY)
        
        existingContentBucket = s3.Bucket(self, 'ExistingDocumentsBucket', versioned= False, auto_delete_objects = True, removal_policy = cdk.RemovalPolicy.DESTROY)
        existingContentBucket.grant_read_write(s3BatchOperationsRole)

        inventoryAndLogsBucket = s3.Bucket(self, 'InventoryAndLogsBucket', versioned= False, auto_delete_objects = True, removal_policy = cdk.RemovalPolicy.DESTROY)
        inventoryAndLogsBucket.grant_read_write(s3BatchOperationsRole)



        # **********DynamoDB Table*************************
        # https://docs.aws.amazon.com/cdk/api/latest/python/aws_cdk.aws_dynamodb/Table.html

        # DynamoDB table with links to output in S3
        outputTable = dynamodb.Table(self, 'OutputTable', 
            partition_key = dynamodb.Attribute(name = 'documentId', type = dynamodb.AttributeType.STRING),
            sort_key = dynamodb.Attribute(name = 'outputType', type = dynamodb.AttributeType.STRING)
        )

        #DynamoDB table with Output-Forms field value pair extraction
        outputForms = dynamodb.Table(self, 'Output-Forms', 
            partition_key = dynamodb.Attribute(name = 'documentId', type = dynamodb.AttributeType.STRING),
            sort_key = dynamodb.Attribute(name = 'pageNumber', type = dynamodb.AttributeType.STRING)
        )


        #DynamoDB table with links to output in S3
        documentsTable = dynamodb.Table(self, 'DocumentsTable', 
            partition_key = dynamodb.Attribute(name = 'documentId', type = dynamodb.AttributeType.STRING),
            stream = dynamodb.StreamViewType.NEW_IMAGE
        )




        # **********SQS Queues*****************************
        # https://docs.aws.amazon.com/cdk/api/latest/python/aws_cdk.aws_sqs/Queue.html

        # Dead Letter Queue (DLQ)
        dlq = sqs.Queue(self, 'DeadLetterQueue',
            visibility_timeout = cdk.Duration.seconds(30), 
            retention_period = cdk.Duration.seconds(1209600)
        )

        # Input Queue for sync jobs
        syncJobsQueue = sqs.Queue(self, 'SyncJobs', 
            visibility_timeout = cdk.Duration.seconds(30), 
            retention_period = cdk.Duration.seconds(1209600), 
            dead_letter_queue = sqs.DeadLetterQueue(queue = dlq, max_receive_count = 50)
        )

        # Input Queue for async jobs
        asyncJobsQueue = sqs.Queue(self, 'AsyncJobs',
            visibility_timeout = cdk.Duration.seconds(30), 
            retention_period = cdk.Duration.seconds(1209600), 
            dead_letter_queue = sqs.DeadLetterQueue(queue = dlq, max_receive_count = 50)
        )

        # Job Results Queue
        jobResultsQueue = sqs.Queue(self, 'JobResults',
            visibility_timeout = cdk.Duration.seconds(900), 
            retention_period = cdk.Duration.seconds(1209600), 
            dead_letter_queue = sqs.DeadLetterQueue(queue = dlq, max_receive_count = 50)
        )

        # Job Completion Trigger
        jobCompletionTopic.add_subscription(
            sns_subscriptions.SqsSubscription(jobResultsQueue)
        )