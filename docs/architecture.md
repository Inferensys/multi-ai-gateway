# Architecture

The gateway is split into three layers:

- deployment inventory
- deterministic routing
- provider execution

## Flow

```text
request
  -> route constraints
  -> candidate ranking
  -> selected deployment + fallback chain
  -> provider execution
  -> response + attempts trace
```

## Why Routing Is App-Owned

Provider-side auto-routing is convenient until you need to explain:

- why a low-risk request landed on the expensive model
- why a release review used the fast lane
- why fallback happened
- what policy changed between two runs

This repo keeps those answers local.

## Deployment Profiles

Each deployment is described with a small policy surface:

- `quality_tier`
- `speed_tier`
- `cost_tier`
- `max_output_tokens`

That is intentionally coarse. The goal is not perfect cost accounting. The goal is stable route behavior that does not depend on a provider-specific pricing page.

## Failure Model

Execution is attempted in order:

1. selected deployment
2. fallback chain in router order

Every attempt is recorded with:

- deployment
- status
- latency
- error if one occurred

If all attempts fail, the gateway raises. It does not synthesize a fake answer.
