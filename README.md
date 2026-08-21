# Second Skin

An always-on autonomous textile pattern design studio, built for the AWS
Builder Center **Weekend Creative Agent Challenge**.

Once a day, Second Skin:
1. Checks the date, day of week, real weather, and the oldest pending
   community-submitted mood word.
2. Writes a design brief (Amazon Bedrock **Nova Lite**) — palette, motif,
   mood — informed by that context *and* by its own rolling memory of the
   last several days' style notes, so its aesthetic visibly drifts over
   time instead of resetting every day.
3. Generates a seamless pattern tile (Amazon Bedrock **Nova Canvas**),
   conditioned on yesterday's tile so today's design is visibly derived
   from it rather than unrelated.
4. Writes a short designer's note, then privately critiques its own work
   into a one-line style note that feeds tomorrow's brief.
5. Publishes the tile, note, and a public "nudge tomorrow's design" mood-word
   box to a static gallery.

See [`docs/RUNBOOK.md`](docs/RUNBOOK.md) for the full build/deploy/verify
walkthrough, and the architecture write-up in the submitted Builder Center
article for the "why" behind each decision.

## Layout

```
infra/       AWS CDK (Python) — all infrastructure
lambdas/     the five Lambda functions + shared common/ code
frontend/    static gallery site (no build step), deployed via Amplify Hosting
scripts/     manual pipeline trigger + history backfill helper
assets/      seed assets (placeholder tile) shipped into S3 at deploy time
docs/        RUNBOOK.md
```

## Quick start

```bash
cd infra
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
npm install --no-save aws-cdk   # or: npm install -g aws-cdk, if you have global npm perms

# confirm Bedrock model access for amazon.nova-lite-v1:0, amazon.nova-micro-v1:0,
# amazon.nova-canvas-v1:0 in your target region (Bedrock console -> Model access) first

npx cdk bootstrap   # first time only, per account/region
npx cdk deploy
```

Then wire the front end (`frontend/js/config.js`) to the two CfnOutputs
(`ManifestUrl`, `SubmitApiUrl`) and connect Amplify Hosting to the repo,
subfolder `frontend/`. Full details in the RUNBOOK.
