# Routing Playbook

This repo fits teams that already know they need a policy boundary before provider execution.

## Good Fit

Use this style of routing when:

- requests have different blast radii
- finance cares about model spend
- platform or product teams need to explain route choice later
- fallback order should be explicit and reviewable
- model choice is a policy decision, not just an SDK setting

Typical examples:

- cheap lane for incident summaries and low-risk internal copilots
- heavy lane for release review, policy-sensitive analysis, or decisions that feed a human approval flow

## Bad Fit

Do not use this repo if:

- you want provider-managed auto-routing and do not care why a route changed
- every request should always hit the same deployment
- the application does not own any notion of risk, cost, or output contract

## Boundary To Protect

Keep these local:

- route constraints
- deployment ranking rules
- fallback order
- rationale string or route trace
- scenario-to-request compilation for the operator workflows you care about

Swap providers if you need to. Do not move the route decision into the provider client unless you are willing to give up auditability.

If operators routinely ask for a route preview before they execute, that preview surface belongs here too.
