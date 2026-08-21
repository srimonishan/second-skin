"""
Smoke test: the stack must synthesize and contain the resources this project
depends on. Not exhaustive -- just enough to catch an obviously broken
construct wiring before a `cdk deploy`.

Run with: pytest (from infra/, with the venv active)
"""
import aws_cdk as cdk
from aws_cdk.assertions import Template

from second_skin_infra.second_skin_stack import SecondSkinStack


def _template() -> Template:
    app = cdk.App()
    stack = SecondSkinStack(app, "TestStack")
    return Template.from_stack(stack)


_OUR_HANDLERS = {
    "fetch_context.handler.handler",
    "generate_brief.handler.handler",
    "generate_image.handler.handler",
    "store_and_evolve.handler.handler",
    "submit_word.handler.handler",
}


def test_five_lambda_functions():
    # CDK's Bucket(auto_delete_objects=True) and BucketDeployment each add
    # their own custom-resource Lambda, so the raw resource count is higher
    # than our 5 app functions -- filter down to ours by handler string.
    resources = _template().find_resources("AWS::Lambda::Function")
    our_handlers = {r["Properties"].get("Handler") for r in resources.values()}
    assert _OUR_HANDLERS <= our_handlers, our_handlers


def test_two_dynamodb_tables():
    _template().resource_count_is("AWS::DynamoDB::Table", 2)


def test_one_state_machine_express():
    template = _template()
    template.resource_count_is("AWS::StepFunctions::StateMachine", 1)
    template.has_resource_properties("AWS::StepFunctions::StateMachine", {"StateMachineType": "EXPRESS"})


def test_one_daily_schedule():
    _template().resource_count_is("AWS::Scheduler::Schedule", 1)


def test_http_api_present():
    _template().resource_count_is("AWS::ApiGatewayV2::Api", 1)


def test_bucket_public_read_scoped_to_prefixes():
    template = _template()
    template.resource_count_is("AWS::S3::Bucket", 1)
    # The bucket policy should exist; a full assertion on its exact scoped
    # resources is brittle against asset hashes, so this is a presence check --
    # see storage.py for the actual `arn_for_objects("tiles/*")` scoping.
    template.resource_count_is("AWS::S3::BucketPolicy", 1)
