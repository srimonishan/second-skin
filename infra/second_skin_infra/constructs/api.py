"""Public HTTP API: POST /submit -> SubmitWordFn. Read paths (manifest.json,
tiles) don't need an API at all -- the front end fetches those straight from
S3 (see storage.py)."""
from aws_cdk import CfnOutput
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import aws_apigatewayv2_integrations as integrations
from constructs import Construct


class SubmissionApi(Construct):
    def __init__(self, scope: Construct, construct_id: str, *, submit_word_fn, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.http_api = apigwv2.HttpApi(
            self, "SubmissionHttpApi",
            cors_preflight=apigwv2.CorsPreflightOptions(
                allow_origins=["*"],
                allow_methods=[apigwv2.CorsHttpMethod.POST, apigwv2.CorsHttpMethod.OPTIONS],
                allow_headers=["Content-Type"],
            ),
        )

        integration = integrations.HttpLambdaIntegration("SubmitWordIntegration", handler=submit_word_fn)
        self.http_api.add_routes(
            path="/submit",
            methods=[apigwv2.HttpMethod.POST],
            integration=integration,
        )

        CfnOutput(self, "SubmitApiUrl", value=f"{self.http_api.api_endpoint}/submit")
