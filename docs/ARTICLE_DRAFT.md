Title: Weekend Creative Agent Challenge: Second Skin
Tag: #agents

---

## Vision: a design studio that never closes

Most "creative AI" demos are things you open, prompt, and wait on. Second Skin is the opposite: it's a textile design studio that works while you're not looking. Once a day, on its own, it invents a new seamless fabric pattern — a palette, a motif, a mood, a designer's note explaining the inspiration — and quietly adds it to a growing gallery. You never prompt it. You just visit and see what the studio made today.

The idea was to take the challenge's four suggested angles — daily output, day/weather theming, community remixing, and improving style over time — and combine all four into one coherent product instead of picking just one. Every day, the studio:

1. Checks the date, day of week, and real weather for its home city.
2. Reads its own private "style memory" — short notes it wrote to itself on previous days — so its aesthetic visibly drifts over time instead of resetting.
3. Writes a design brief (palette, motif, mood) with Amazon Bedrock, informed by all of the above, plus the oldest word a visitor has submitted through the site's "nudge tomorrow's design" box.
4. Generates an actual seamless pattern tile with Amazon Bedrock Nova Canvas, conditioned on yesterday's tile so today's design is visibly derived from it.
5. Privately critiques its own output into a one-line style note that becomes tomorrow's memory.
6. Publishes everything to a static gallery.

## How I built it

I designed this the way I'd design a production system, not a demo script: small single-purpose Lambda functions orchestrated by AWS Step Functions, not one giant handler. Each step — fetch context, generate brief, generate image, store and evolve — is its own function with its own narrowly-scoped IAM permissions (no `*` resource ARNs anywhere; each Lambda can only touch the exact model, table, or S3 prefix it needs). The whole thing is defined in AWS CDK (Python) so it's reproducible and version-controlled, not clicked together in a console.

The key architectural decision was resilience: every Bedrock call in the state machine has a Retry policy and a Catch fallback. If context-fetching fails, the pipeline falls back to sane defaults. If brief generation fails, it falls back to a templated brief. If image generation fails, it publishes with a placeholder tile instead of losing the whole day. Only a genuine persistence failure is allowed to fail the run outright.

That design turned out to matter more than I expected, for a very real reason: my brand-new AWS account's Bedrock on-demand quota came provisioned at literally zero requests-per-minute for Nova Micro, Nova Lite, and Nova Canvas, even with model access granted. Every real generation call throttles until AWS approves a support-ticket quota increase — which, as I write this, is still pending. Rather than let that block the whole submission, I got to watch my own fallback design do exactly what it was built for, live, under a genuine (not staged) failure: the Step Functions execution still completed successfully, publishing a fully-formed entry with a templated brief and a placeholder tile instead of crashing. The DynamoDB record, the public gallery, and the community submission box are all live and working right now — the only piece waiting on AWS is the actual generative call itself, and the architecture is already wired to switch over to real output the instant that clears, with zero redeploy needed.

The community submission box was the other interesting piece: it runs visitor-submitted words through a cheap moderation classification call before queueing them, and — deliberately — fails *closed* by default (rejecting, not silently accepting, if the moderation check itself is unavailable) so unmoderated text never sits in a queue that later feeds an LLM prompt unattended.

## AWS services used

Amazon Bedrock (Nova Lite for text, Nova Micro for moderation, Nova Canvas for images) · AWS Step Functions (Express workflow, the orchestration backbone) · AWS Lambda (five single-purpose Python functions) · Amazon EventBridge Scheduler (daily trigger) · Amazon DynamoDB (design history + community word queue) · Amazon S3 (tile images + a manifest.json the front end reads directly, no read API needed) · Amazon API Gateway (HTTP API for community submissions) · AWS Amplify Hosting (the public static gallery) · AWS CDK (Python) for all of it as code · Amazon CloudWatch Logs for Express workflow visibility.

## What I learned

The most useful lesson had nothing to do with prompting and everything to do with account readiness: a brand-new AWS account's Bedrock throttle limits can start at zero even with model access explicitly granted, and fixing that runs through a support case, not a self-service quota bump — worth checking days before a deadline, not the morning of. The second lesson is more of a confirmation: designing for graceful degradation from day one, rather than bolting it on later, is what let this project survive a real, unplanned infrastructure failure and still ship something live and functional instead of a blank page.

**Live app:** https://Master.d31ep68fyf014s.amplifyapp.com/
**GitHub:** https://github.com/srimonishan/second-skin
