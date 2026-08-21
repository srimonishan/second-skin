"""
The five Lambda functions. No Lambda Layer, no Docker bundling -- every
handler only needs boto3 (bundled in the Python runtime) plus stdlib, so
Code.from_asset() on the whole lambdas/ directory is enough for
lambdas/common/ to be importable as a sibling package inside each zip.

IAM is intentionally NOT done via broad `table.grant_read_write_data()` /
`bucket.grant_read_write()` calls everywhere -- see the inline comments below
for where an explicit, narrowly-scoped PolicyStatement is used instead.
"""
import os

from aws_cdk import Duration, Stack
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_iam as iam
from constructs import Construct

from .. import config

_LAMBDAS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "lambdas"))


class LambdaFunctions(Construct):
    def __init__(self, scope: Construct, construct_id: str, *, storage, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        region = Stack.of(self).region

        common_env = {
            "DESIGNS_TABLE_NAME": storage.designs_table.table_name,
            "WORDS_TABLE_NAME": storage.words_table.table_name,
            "ASSETS_BUCKET_NAME": storage.bucket.bucket_name,
            "WEATHER_LAT": config.DEFAULT_WEATHER_LAT,
            "WEATHER_LON": config.DEFAULT_WEATHER_LON,
            "WEATHER_LOCATION_NAME": config.DEFAULT_WEATHER_LOCATION_NAME,
        }

        code = _lambda.Code.from_asset(_LAMBDAS_DIR)
        runtime = _lambda.Runtime.PYTHON_3_12

        # ---- FetchContext ---------------------------------------------
        self.fetch_context = _lambda.Function(
            self, "FetchContextFn",
            runtime=runtime, code=code, handler="fetch_context.handler.handler",
            timeout=Duration.seconds(20), memory_size=256,
            environment=dict(common_env),
        )
        # Only needs to read: recent style notes + latest design (Scan on
        # SecondSkinDesigns) and the oldest pending word (Query on
        # CommunityWords' GSI). grant_read_data() covers table + index reads.
        storage.designs_table.grant_read_data(self.fetch_context)
        storage.words_table.grant_read_data(self.fetch_context)

        # ---- GenerateBrief ----------------------------------------------
        self.generate_brief = _lambda.Function(
            self, "GenerateBriefFn",
            runtime=runtime, code=code, handler="generate_brief.handler.handler",
            timeout=Duration.seconds(30), memory_size=256,
            environment={**common_env, "TEXT_MODEL_ID": config.TEXT_MODEL_ID},
        )
        self.generate_brief.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=[config.model_arn(region, config.TEXT_MODEL_ID)],
        ))

        # ---- GenerateImage ------------------------------------------------
        self.generate_image = _lambda.Function(
            self, "GenerateImageFn",
            runtime=runtime, code=code, handler="generate_image.handler.handler",
            timeout=Duration.seconds(60), memory_size=512,
            environment={**common_env, "IMAGE_MODEL_ID": config.IMAGE_MODEL_ID},
        )
        self.generate_image.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=[config.model_arn(region, config.IMAGE_MODEL_ID)],
        ))
        # Reads yesterday's tile (for image-conditioning) and writes today's --
        # scoped to the tiles/ prefix only, never the whole bucket.
        self.generate_image.add_to_role_policy(iam.PolicyStatement(
            actions=["s3:GetObject", "s3:PutObject"],
            resources=[storage.bucket.arn_for_objects("tiles/*")],
        ))

        # ---- StoreAndEvolve -----------------------------------------------
        self.store_and_evolve = _lambda.Function(
            self, "StoreAndEvolveFn",
            runtime=runtime, code=code, handler="store_and_evolve.handler.handler",
            timeout=Duration.seconds(30), memory_size=256,
            environment={**common_env, "TEXT_MODEL_ID": config.TEXT_MODEL_ID},
        )
        self.store_and_evolve.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=[config.model_arn(region, config.TEXT_MODEL_ID)],
        ))
        # Writes today's record + reads the whole table back to rebuild
        # manifest.json -- grant_read_write_data is appropriate here since
        # both Put (one item) and Scan (rebuild) are genuinely needed.
        storage.designs_table.grant_read_write_data(self.store_and_evolve)
        # Only ever flips one attribute on one already-known item by PK --
        # UpdateItem only, not the broader write grant.
        self.store_and_evolve.add_to_role_policy(iam.PolicyStatement(
            actions=["dynamodb:UpdateItem"],
            resources=[storage.words_table.table_arn],
        ))
        # Only regenerates manifest.json -- the tile PNG itself was already
        # written by GenerateImage, so no tiles/* access needed here.
        self.store_and_evolve.add_to_role_policy(iam.PolicyStatement(
            actions=["s3:PutObject"],
            resources=[storage.bucket.arn_for_objects("manifest.json")],
        ))

        # ---- SubmitWord (API Gateway target, not part of the SFN chain) ---
        self.submit_word = _lambda.Function(
            self, "SubmitWordFn",
            runtime=runtime, code=code, handler="submit_word.handler.handler",
            timeout=Duration.seconds(15), memory_size=256,
            environment={**common_env, "MODERATION_MODEL_ID": config.MODERATION_MODEL_ID},
        )
        self.submit_word.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=[config.model_arn(region, config.MODERATION_MODEL_ID)],
        ))
        # Only ever creates a new item -- PutItem only.
        self.submit_word.add_to_role_policy(iam.PolicyStatement(
            actions=["dynamodb:PutItem"],
            resources=[storage.words_table.table_arn],
        ))
