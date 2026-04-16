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

The gateway decides from application-owned inputs:

- `routing_mode`
- `risk_level`
- `requires_json`
- optional cost ceiling
- optional deployment allow-list

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
    "rationale": "routing_mode=quality, risk_level=high, selected=gpt-5.4(quality=5,speed=2,cost=3)"
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

Or replay from the CLI:

```bash
uv run mag complete \
  --input-file demo/input/release-risk.json \
  --out /tmp/release-risk.json
```

## Python Entry Point

```python
from multi_ai_gateway import AzureChatProvider, Gateway, GatewayRequest, Settings, ChatMessage

settings = Settings.from_env()
gateway = Gateway(
    provider=AzureChatProvider(settings),
    deployments=settings.default_deployments(),
)

response = gateway.complete(
    GatewayRequest(
        routing_mode="quality",
        risk_level="high",
        messages=[
            ChatMessage(
                role="system",
                content="Give a direct ship or hold recommendation with operational risks.",
            ),
            ChatMessage(role="user", content="Review the rollout note."),
        ],
    )
)

print(response.deployment)
print(response.route.rationale)
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
