#!/usr/bin/env python3
import aws_cdk as cdk

from second_skin_infra.second_skin_stack import SecondSkinStack

app = cdk.App()

SecondSkinStack(
    app,
    "SecondSkinStack",
    description="Second Skin -- an always-on autonomous textile pattern design agent (AWS Weekend Creative Agent Challenge).",
    # env=cdk.Environment(account=os.environ["CDK_DEFAULT_ACCOUNT"], region=os.environ["CDK_DEFAULT_REGION"]),
    # ^ uncomment to pin the stack to your `aws configure` account/region explicitly;
    #   left unset here so `cdk deploy` uses whatever the active AWS CLI profile resolves to.
)

app.synth()
