"""
The Express state machine: FetchContext -> GenerateBrief -> GenerateImage ->
StoreAndEvolve, each with a Retry and a Catch. Every Catch uses
`result_path=JsonPath.DISCARD` so the ORIGINAL input to that task passes
through unchanged into its fallback Pass state (error details are dropped,
not merged) -- this keeps every fallback Pass state able to reference the
upstream fields it needs (e.g. `$.date`, `$.brief`) via plain JsonPath
references instead of fragile ResultPath merging.

Only StoreAndEvolve's Catch leads to a hard Fail: if nothing could be
persisted, the run genuinely produced nothing worth publishing.
"""
from aws_cdk import Duration, Stack
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as tasks
from aws_cdk import aws_logs as logs
from constructs import Construct

_LAMBDA_RETRY_ERRORS = [
    "Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException", "States.Timeout",
]


class SecondSkinStateMachine(Construct):
    def __init__(self, scope: Construct, construct_id: str, *, fns, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ---- Fallback Pass states -----------------------------------------

        use_default_context = sfn.Pass(
            self, "UseDefaultContext",
            comment="FetchContext failed even after retry -- fall back to 'today' (derived from the execution's own entry time) with empty/unknown context so the run can still produce something.",
            parameters={
                # $$.State.EnteredTime is an ISO8601 string like 2026-08-21T12:00:03.456Z;
                # split on 'T' and take element 0 to get the YYYY-MM-DD date part.
                "date.$": "States.ArrayGetItem(States.StringSplit($$.State.EnteredTime, 'T'), 0)",
                "dayOfWeek": "Unknown",
                "weatherSummary": "unknown weather",
                "communityWord": None,
                "communityWordId": None,
                "styleMemory": [],
                "previousImageKey": None,
                "contextFallbackUsed": True,
            },
        )

        generate_brief_fallback = sfn.Pass(
            self, "GenerateBriefFallback",
            comment="GenerateBrief failed even after retry -- use a plain templated brief instead of failing the whole run.",
            parameters={
                "date.$": "$.date",
                "dayOfWeek.$": "$.dayOfWeek",
                "weatherSummary.$": "$.weatherSummary",
                "communityWord.$": "$.communityWord",
                "communityWordId.$": "$.communityWordId",
                "styleMemory.$": "$.styleMemory",
                "previousImageKey.$": "$.previousImageKey",
                "contextFallbackUsed.$": "$.contextFallbackUsed",
                "brief": {"palette": "muted neutrals", "motif": "simple repeating grid", "mood": "quiet"},
                "designerNote": "The studio kept things simple today while the usual design process was unavailable.",
                "briefFallbackUsed": True,
            },
        )

        use_placeholder_image = sfn.Pass(
            self, "UsePlaceholderImage",
            comment="GenerateImage failed even after retry -- publish today's brief/note with the placeholder tile rather than losing the whole run.",
            parameters={
                "date.$": "$.date",
                "dayOfWeek.$": "$.dayOfWeek",
                "weatherSummary.$": "$.weatherSummary",
                "communityWord.$": "$.communityWord",
                "communityWordId.$": "$.communityWordId",
                "styleMemory.$": "$.styleMemory",
                "previousImageKey.$": "$.previousImageKey",
                "contextFallbackUsed.$": "$.contextFallbackUsed",
                "brief.$": "$.brief",
                "designerNote.$": "$.designerNote",
                "briefFallbackUsed.$": "$.briefFallbackUsed",
                "imageKey": "tiles/placeholder.png",
                "imageGenerated": False,
            },
        )

        persist_failed = sfn.Fail(
            self, "PersistFailed",
            comment="StoreAndEvolve failed even after retry -- nothing was saved, so there is no meaningful fallback; this run genuinely produced nothing.",
            error="PersistFailed",
            cause="StoreAndEvolve could not write the day's record after retrying.",
        )

        # ---- Task states ----------------------------------------------------

        fetch_context_task = tasks.LambdaInvoke(
            self, "FetchContext", lambda_function=fns.fetch_context, output_path="$.Payload",
        )
        fetch_context_task.add_retry(errors=_LAMBDA_RETRY_ERRORS, interval=Duration.seconds(2), backoff_rate=2.0, max_attempts=2)
        fetch_context_task.add_catch(use_default_context, errors=["States.ALL"], result_path=sfn.JsonPath.DISCARD)

        generate_brief_task = tasks.LambdaInvoke(
            self, "GenerateBrief", lambda_function=fns.generate_brief, output_path="$.Payload",
        )
        generate_brief_task.add_retry(errors=_LAMBDA_RETRY_ERRORS, interval=Duration.seconds(2), backoff_rate=2.0, max_attempts=3)
        generate_brief_task.add_catch(generate_brief_fallback, errors=["States.ALL"], result_path=sfn.JsonPath.DISCARD)

        generate_image_task = tasks.LambdaInvoke(
            self, "GenerateImage", lambda_function=fns.generate_image, output_path="$.Payload",
        )
        generate_image_task.add_retry(errors=_LAMBDA_RETRY_ERRORS, interval=Duration.seconds(3), backoff_rate=2.0, max_attempts=2)
        generate_image_task.add_catch(use_placeholder_image, errors=["States.ALL"], result_path=sfn.JsonPath.DISCARD)

        store_and_evolve_task = tasks.LambdaInvoke(
            self, "StoreAndEvolve", lambda_function=fns.store_and_evolve, output_path="$.Payload",
        )
        store_and_evolve_task.add_retry(errors=_LAMBDA_RETRY_ERRORS, interval=Duration.seconds(2), backoff_rate=2.0, max_attempts=2)
        store_and_evolve_task.add_catch(persist_failed, errors=["States.ALL"], result_path=sfn.JsonPath.DISCARD)

        # ---- Wire the chain ---------------------------------------------------

        use_default_context.next(generate_brief_task)
        generate_brief_fallback.next(generate_image_task)
        use_placeholder_image.next(store_and_evolve_task)

        definition = fetch_context_task.next(generate_brief_task).next(generate_image_task).next(store_and_evolve_task)

        log_group = logs.LogGroup(self, "StateMachineLogs", retention=logs.RetentionDays.TWO_WEEKS)

        self.state_machine = sfn.StateMachine(
            self, "PipelineStateMachine",
            state_machine_type=sfn.StateMachineType.EXPRESS,
            definition_body=sfn.DefinitionBody.from_chainable(definition),
            timeout=Duration.minutes(5),
            logs=sfn.LogOptions(destination=log_group, level=sfn.LogLevel.ALL, include_execution_data=True),
        )
