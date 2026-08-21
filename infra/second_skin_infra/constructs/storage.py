"""
S3 bucket (public-read only on the two asset prefixes it actually serves)
and the two DynamoDB tables. Nothing else in this stack should ever get
broad access to this bucket -- see lambdas.py for the scoped per-function
IAM statements.
"""
from aws_cdk import CfnOutput, RemovalPolicy
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from constructs import Construct


class Storage(Construct):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.bucket = s3.Bucket(
            self, "AssetsBucket",
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=False,
                block_public_policy=False,
                ignore_public_acls=False,
                restrict_public_buckets=False,
            ),
            cors=[s3.CorsRule(
                allowed_methods=[s3.HttpMethods.GET],
                allowed_origins=["*"],
                allowed_headers=["*"],
                max_age=3000,
            )],
            removal_policy=RemovalPolicy.DESTROY,  # weekend project -- fine to tear down cleanly; revisit if this becomes long-lived
            auto_delete_objects=True,
        )

        # Public read ONLY on the two prefixes the front end actually needs --
        # never a bucket-wide GetObject grant.
        self.bucket.add_to_resource_policy(iam.PolicyStatement(
            sid="PublicReadTilesAndManifest",
            effect=iam.Effect.ALLOW,
            principals=[iam.AnyPrincipal()],
            actions=["s3:GetObject"],
            resources=[
                self.bucket.arn_for_objects("tiles/*"),
                self.bucket.arn_for_objects("manifest.json"),
            ],
        ))

        self.designs_table = dynamodb.Table(
            self, "SecondSkinDesigns",
            partition_key=dynamodb.Attribute(name="date", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.words_table = dynamodb.Table(
            self, "CommunityWords",
            partition_key=dynamodb.Attribute(name="id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )
        self.words_table.add_global_secondary_index(
            index_name="StatusIndex",
            partition_key=dynamodb.Attribute(name="status", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="submittedAt", type=dynamodb.AttributeType.NUMBER),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        CfnOutput(self, "AssetsBucketName", value=self.bucket.bucket_name)
        CfnOutput(self, "ManifestUrl", value=f"https://{self.bucket.bucket_name}.s3.amazonaws.com/manifest.json")
