# Second Skin — Runbook

## 0. Tooling & AWS account setup

- Install the AWS CLI v2 and configure credentials: `aws configure`.
- In the **Bedrock console** → *Model access*, in the region you intend to
  deploy to, request/confirm access to:
  - `amazon.nova-lite-v1:0`
  - `amazon.nova-micro-v1:0`
  - `amazon.nova-canvas-v1:0`
  Access can take a few minutes to propagate — do this before writing more
  code or deploying, not after something fails.
- `cd infra && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- `npm install --no-save aws-cdk` (local install avoids needing global npm
  permissions; invoke it as `npx cdk ...` throughout, or `npm install -g
  aws-cdk` if you do have global perms).
- `npx cdk bootstrap` — one-time per AWS account/region.

## 1. Deploy the stack

```bash
cd infra
source .venv/bin/activate
npx cdk synth      # sanity check — should produce cdk.out/ with no errors
npx cdk deploy
```

Note the two important `CfnOutput`s printed at the end of `deploy`:
`ManifestUrl` and `SubmitApiUrl` (plus `AssetsBucketName` and
`StateMachineArn`, useful for the manual-trigger scripts).

The placeholder tile (`assets/placeholder.png`) ships automatically via
`BucketDeployment` as part of this deploy — no manual S3 upload step needed.

## 2. Wire and deploy the front end

Edit `frontend/js/config.js`:
```js
const MANIFEST_URL = "<ManifestUrl output>";
const SUBMIT_API_URL = "<SubmitApiUrl output>";
```

Commit, push to a GitHub repo, then in the Amplify Hosting console: connect
the repo, set the app root / monorepo subfolder to `frontend/` (it uses the
included `amplify.yml`, which has no real build step). First deploy takes a
couple of minutes; note the `*.amplifyapp.com` URL.

## 3. Run the pipeline manually (dev iteration + demo)

```bash
./scripts/invoke_pipeline.sh                # runs for "today"
./scripts/invoke_pipeline.sh 2026-08-19     # backfill a specific date
```

This calls `aws stepfunctions start-sync-execution`, which blocks and
prints the full output (or error) inline — the fastest feedback loop while
building, and the same command works live in front of judges.

Watch logs while it runs:
```bash
aws logs tail /aws/vendedlogs/states/<log-group-name> --follow
```
(Express workflows don't have a persistent execution-history view in the
console the way Standard workflows do — CloudWatch Logs is the real window
into what happened.)

## 4. Seed history so the gallery isn't empty at demo time

```bash
python3 scripts/seed_history.py --days 3
```

Runs oldest-date-first so each day's image-conditioning reference and style
memory genuinely exist by the time the next date runs.

## 5. Verification checklist

- [ ] `aws s3 ls s3://<bucket>/tiles/` shows a new object after a run.
- [ ] `aws s3 cp s3://<bucket>/manifest.json -` shows the new entry first
      (newest-first ordering).
- [ ] `aws dynamodb get-item --table-name <SecondSkinDesigns table> --key '{"date":{"S":"<date>"}}'`
      shows the full record.
- [ ] Amplify URL: gallery shows the new tile, detail page renders the
      note/badges, "Download this tile" link resolves (a 403 here means the
      bucket policy/CORS scoping needs a look).
- [ ] **Community round-trip**: submit a word via the live form → confirm it
      shows `pending` in `CommunityWords` → run the pipeline manually →
      confirm it appears as that day's `communityWordUsed` and flips to
      `used` → run again and confirm it is *not* reused.
- [ ] **Fallback proof** (do this once deliberately, then restore): break
      `GenerateImage` (e.g. temporarily set its `IMAGE_MODEL_ID` env var in
      the Lambda console to a bogus value), run the pipeline, confirm the
      execution still reaches `Success` with `imageGenerated: false` and the
      placeholder tile rather than failing outright. Screenshot the
      CloudWatch log / Step Functions graph showing the Catch transition —
      this is the concrete evidence of the resilience design for the
      article write-up.
- [ ] Cost sanity check in Cost Explorer / Bedrock usage after a weekend of
      iteration — expect low single digits of dollars.

## Known things worth a second look before/while building

- **Nova Canvas request schema** (`lambdas/generate_image/handler.py`): the
  `TEXT_IMAGE` / `IMAGE_VARIATION` body shape was confirmed against
  `docs.aws.amazon.com/nova/latest/userguide/image-gen-req-resp-structure.html`
  at build time, but Bedrock docs do shift between revisions — re-check that
  page if `InvokeModel` ever returns a validation error here.
- **Model ARNs / regional access** (`infra/second_skin_infra/config.py`):
  if `InvokeModel` fails with an on-demand-throughput error, the model may
  need a cross-region inference profile ARN in your region instead of the
  bare foundation-model ARN — see the comment in `config.py`.
- **EventBridge Scheduler time**: `SCHEDULE_CRON_HOUR_UTC` /
  `SCHEDULE_CRON_MINUTE_UTC` in `config.py` default to 12:00 UTC — adjust to
  whenever you'd actually like a fresh tile waiting for you.
- **Weather location**: defaults to London via `config.py` /
  `WEATHER_LAT`/`WEATHER_LON`/`WEATHER_LOCATION_NAME` env vars — change if
  you'd rather theme the studio to your own city.
