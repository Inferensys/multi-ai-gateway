# multi-ai-gateway

This repo is about one control point:

deciding when a request is safe to send through the cheap lane and when it needs the heavier model before you call any provider at all.

The checked scenarios in this repo come from two different operator contexts:

- a low-risk incident summary that should stay on the fast lane
- a high-risk release review that should route to the heavier model because the blast radius is larger than the token bill

## Open These First

- `demo/input/release-risk.json`
- `demo/output/release-risk.json`
- `demo/input/fast-triage.json`
- `demo/output/demo-summary.json`

If the route choices in those files look defensible, the rest of the repo is doing its job.

## The Routing Question

The gateway decides from application-owned inputs.

At the low level that is still:

- `routing_mode`
- `risk_level`
- `requires_json`
- optional cost ceiling
- optional deployment allow-list

But the repo now exposes domain-shaped scenario inputs for the two workflows it actually demonstrates:

- `incident_triage`
- `release_review`

That is enough to answer the question the repo actually cares about:

can this request be served cheaply without being irresponsible?

The checked `release-risk` scenario answers no. It routes to `gpt-5.4` and leaves `gpt-5-mini` as fallback because the request touches session rotation, async fraud scoring, payment retry behavior, and a known duplicate-capture failure mode before quarter-close traffic.

## What The Checked Run Shows

The live run produced two outputs:

- `fast-triage`
  low risk, cost constrained, routed to `gpt-5-mini`

- `release-risk`
  high risk, quality lane selected, routed to `gpt-5.4`

Rendered captures:

![Gateway route summary](assets/demo-summary-card.svg)
![Release risk route](assets/release-risk-route.svg)

Summary from `demo/output/demo-summary.json`:

```json
[
  {
    "name": "fast-triage",
    "deployment": "gpt-5-mini",
    "latency_ms": 20431,
    "total_tokens": 614,
    "fallbacks_used": 0
  },
  {
    "name": "release-risk",
    "deployment": "gpt-5.4",
    "latency_ms": 13531,
    "total_tokens": 528,
    "fallbacks_used": 0
  }
]
```

The most useful checked artifact is `demo/output/release-risk.json` because it contains both the served answer and the route trace:

```json
{
  "deployment": "gpt-5.4",
  "route": {
    "selected_deployment": "gpt-5.4",
    "fallback_chain": ["gpt-5-mini"],
    "policy_name": "high-blast-radius-review",
    "why_not_lower_tier": [
      "blast radius is money_movement",
      "release reviews default to the heavier lane when risk is high"
    ]
  }
}
```

## Why The Route Stays Local

This project is not trying to be a universal proxy.

It exists because teams usually need to explain:

- why an incident summary used the cheap lane
- why a release review did not
- what changed when a route changed
- what fallback order was attempted

Provider-side auto-routing cannot usually answer those questions in application terms. This repo can, because the policy stays in the router.

## Run The Exact Scenarios

Install:

```bash
uv sync --extra dev
```

Set Azure variables:

```bash
export AZURE_OPENAI_ENDPOINT="https://<resource>.openai.azure.com/"
export AZURE_OPENAI_API_KEY="<key>"
export AZURE_OPENAI_API_VERSION="2025-04-01-preview"
export MULTI_AI_GATEWAY_FAST_DEPLOYMENT="gpt-5-mini"
export MULTI_AI_GATEWAY_QUALITY_DEPLOYMENT="gpt-5.4"
```

Regenerate the checked demo:

```bash
uv run python scripts/run_live_demo.py
```

That will rewrite the JSON in `demo/output/`.

## Run It As A Service

```bash
uv run uvicorn multi_ai_gateway.main:app --app-dir src --reload
```

Send the high-risk release scenario:

```bash
curl -sS http://127.0.0.1:8000/v1/complete \
  -H "content-type: application/json" \
  -d @demo/input/release-risk.json
```

Preview the route without spending tokens:

```bash
curl -sS http://127.0.0.1:8000/v1/route-preview \
  -H "content-type: application/json" \
  -d @demo/input/release-risk.json
```

Use the scenario endpoints directly:

```bash
curl -sS http://127.0.0.1:8000/v1/scenarios/incident-triage \
  -H "content-type: application/json" \
  -d @demo/input/fast-triage.json
```

Or replay from the CLI:

```bash
uv run mag preview \
  --input-file demo/input/release-risk.json \
  --out /tmp/release-risk.preview.json
```

```bash
uv run mag complete \
  --input-file demo/input/release-risk.json \
  --out /tmp/release-risk.response.json
```

## Python Entry Point

```python
from multi_ai_gateway import AzureChatProvider, Gateway, ReleaseReviewScenario, Settings

settings = Settings.from_env()
gateway = Gateway(
    provider=AzureChatProvider(settings),
    deployments=settings.default_deployments(),
)

request = ReleaseReviewScenario(
    release_id="REL-742",
    system_scope="payments checkout",
    change_summary=[
        "session token rotation changed",
        "fraud scoring moved to async queue",
        "new payment retry branch added",
    ],
    evidence_gaps=["no full-region failover test"],
    historical_failures=["duplicate-capture"],
    timing_pressure="quarter-close traffic starts tomorrow",
    blast_radius="money_movement",
).to_gateway_request()

decision = gateway.preview(request)
response = gateway.complete(request)

print(decision.policy_name)
print(decision.why_not_lower_tier)
print(response.deployment)
print(response.route.rationale)
```

If you still want the lower-level interface, it remains available:

```python
from multi_ai_gateway import ChatMessage, GatewayRequest

request = GatewayRequest(
    messages=[ChatMessage(role="user", content="Summarize the incident.")],
    routing_mode="latency",
    risk_level="low",
)
```

## Repo Map

- `src/multi_ai_gateway/router.py`
  Ranking logic, rationale construction, fallback order.

- `src/multi_ai_gateway/gateway.py`
  Execution loop and attempt trace handling.

- `src/multi_ai_gateway/azure_provider.py`
  Azure-backed completion path.

- `demo/README.md`
  How to inspect the two checked scenarios.

- `docs/routing-playbook.md`
  When this routing style is useful and where it should stop.

- `docs/azure-foundry.md`
  Deployment split used for the live run.

## Verify

```bash
uv run pytest -q
```
