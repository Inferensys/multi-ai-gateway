# Demo Guide

This demo has two intentionally different requests.

## 1. Fast Triage

Open:

- `input/fast-triage.json`
- `output/fast-triage.json`

This input is now a structured `incident_triage` scenario, not a raw prompt blob.

It is the cheap-lane case:

- low-risk operational summary
- no structured contract
- explicit cost ceiling

If this does not route to the fast deployment, the policy is probably too conservative.

## 2. Release Risk

Open:

- `input/release-risk.json`
- `output/release-risk.json`

This input is a structured `release_review` scenario.

It is the heavy-lane case:

- higher blast radius
- known historical failure mode
- release timing pressure
- operational downside if the answer is shallow

If this does not route to the heavier deployment, the policy is probably too aggressive on cost.

## 3. Compare Them

Finally open:

- `output/demo-summary.json`

The interesting thing is not that two models were called. The interesting thing is that the router made two different decisions from a very small policy surface and preserved the rationale.

If you want to inspect the decision without executing the provider call, run:

```bash
uv run mag preview \
  --input-file demo/input/release-risk.json \
  --out /tmp/release-risk.preview.json
```
