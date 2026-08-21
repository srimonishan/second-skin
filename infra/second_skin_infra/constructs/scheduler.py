"""
EventBridge Scheduler: fires the pipeline once a day. Uses the L1
`CfnSchedule` construct directly (the L2 scheduler constructs still live in
an alpha package versioned separately from aws-cdk-lib, which is an extra
dependency-pinning headache not worth it for one resource) with a role
scoped to `states:StartExecution` on this one state machine ARN only.
"""
import json

from aws_cdk import aws_iam as iam
from aws_cdk import aws_scheduler as scheduler
from constructs import Construct

from .. import config


class DailySchedule(Construct):
    def __init__(self, scope: Construct, construct_id: str, *, state_machine, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        role = iam.Role(
            self, "SchedulerRole",
            assumed_by=iam.ServicePrincipal("scheduler.amazonaws.com"),
        )
        role.add_to_policy(iam.PolicyStatement(
            actions=["states:StartExecution"],
            resources=[state_machine.state_machine_arn],
        ))

        self.schedule = scheduler.CfnSchedule(
            self, "DailyRun",
            flexible_time_window=scheduler.CfnSchedule.FlexibleTimeWindowProperty(mode="OFF"),
            schedule_expression=f"cron({config.SCHEDULE_CRON_MINUTE_UTC} {config.SCHEDULE_CRON_HOUR_UTC} * * ? *)",
            schedule_expression_timezone="UTC",
            state="ENABLED",
            target=scheduler.CfnSchedule.TargetProperty(
                arn=state_machine.state_machine_arn,
                role_arn=role.role_arn,
                input=json.dumps({}),
            ),
        )
