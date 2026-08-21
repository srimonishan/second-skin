from aws_cdk import CfnOutput, Stack
from constructs import Construct

from .constructs.storage import Storage
from .constructs.lambdas import LambdaFunctions
from .constructs.state_machine import SecondSkinStateMachine
from .constructs.api import SubmissionApi
from .constructs.scheduler import DailySchedule


class SecondSkinStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        storage = Storage(self, "Storage")
        fns = LambdaFunctions(self, "Lambdas", storage=storage)
        pipeline = SecondSkinStateMachine(self, "Pipeline", fns=fns)
        SubmissionApi(self, "Api", submit_word_fn=fns.submit_word)
        DailySchedule(self, "Schedule", state_machine=pipeline.state_machine)

        # Exposed for scripts/invoke_pipeline.sh and for the CfnOutput below.
        self.state_machine_arn = pipeline.state_machine.state_machine_arn
        CfnOutput(self, "StateMachineArn", value=self.state_machine_arn)
