# Multi-AI Gateway

Unified **LLM routing gateway** with intelligent model selection, automatic failover, budget controls, and unified API across OpenAI, Anthropic, Google, and self-hosted models.

Solves the problem of managing multiple AI providers in production without vendor lock-in or brittle provider switching.

## The Problem

Teams running AI in production face provider complexity:

```python
# Without a gateway
if use_openai:
    import openai
    response = openai.chat.completions.create(...)
elif use_anthropic:
    import anthropic
    response = anthropic.messages.create(...)
# Different APIs, different error handling, different retry logic
```

Issues:
- Inconsistent APIs across providers
- No automatic failover when one provider is down
- Can't optimize cost/performance by routing to best model
- Rate limits hit unexpectedly
- No unified observability

## What This Provides

```
           Client Requests
                  ↓
        ┌─────────────────────┐
        │   Multi-AI Gateway  │
        │  - Router/Smart     │
        │  - Load Balancer    │
        │  - Fallback Engine  │
        └──────────┬──────────┘
                   ↓
    ┌──────────────┼──────────────┐
    ↓              ↓              ↓
 OpenAI      Anthropic      Self-Hosted
  GPT-4      Claude-3      Llama/Qwen
```

## Quick Start

```bash
pip install multi-ai-gateway
```

```python
from multi_ai_gateway import Gateway, RoutingStrategy

# Initialize gateway with providers
gateway = Gateway(providers=[
    {
        "name": "openai",
        "api_key": os.getenv("OPENAI_API_KEY"),
        "models": ["gpt-4", "gpt-4o", "gpt-3.5-turbo"],
        "priority": 1
    },
    {
        "name": "anthropic", 
        "api_key": os.getenv("ANTHROPIC_API_KEY"),
        "models": ["claude-3-opus", "claude-3-sonnet"],
        "priority": 2
    },
    {
        "name": "ollama",
        "base_url": "http://localhost:11434",
        "models": ["llama3", "mixtral"],
        "priority": 3
    }
])

# Unified API regardless of provider
response = gateway.complete(
    messages=[
        {"role": "user", "content": "Explain quantum computing"}
    ],
    model="auto",  # Let gateway choose
    strategy=RoutingStrategy.CHEAPEST
)

print(response.content)
print(response.model)      # Which model actually served it
print(response.provider)   # Which provider
print(response.latency_ms) # Response time
```

## Routing Strategies

### Cost-Optimized

```python
response = gateway.complete(
    messages=messages,
    max_cost_per_1k_tokens=0.01,
    strategy=RoutingStrategy.CHEAPEST
)
```

### Latency-Optimized

```python
response = gateway.complete(
    messages=messages,
    max_latency_ms=2000,
    strategy=RoutingStrategy.FASTEST
)
```

### Quality-Optimized

```python
response = gateway.complete(
    messages=messages,
    task_complexity="high",  # Routes to best model
    strategy=RoutingStrategy.BEST_QUALITY
)
```

### Fallback Chain

```python
response = gateway.complete(
    messages=messages,
    fallback_chain=[
        {"model": "gpt-4", "provider": "openai"},
        {"model": "claude-3-opus", "provider": "anthropic"},
        {"model": "llama3", "provider": "ollama"}
    ]
)
```

## Features

### Automatic Failover

```python
# Built-in retry and fallback
gateway.complete(
    messages=messages,
    retry_policy={
        "max_retries": 3,
        "backoff": "exponential",
        "retry_on": ["rate_limit", "timeout", "server_error"]
    },
    failover_threshold=2  # Failover after 2 failures
)
```

### Load Balancing

```python
# Distribute across multiple instances
gateway = Gateway(
    providers=[
        {"name": "openai_1", "api_key": "...", "weight": 0.5},
        {"name": "openai_2", "api_key": "...", "weight": 0.5}
    ],
    load_balancer="round_robin"  # or "least_connections", "weighted"
)
```

### Budget Controls

```python
# Per-key or per-app budget tracking
gateway.set_budget(
    api_key="pk_abc123",
    daily_limit=100.0,  # USD
    monthly_limit=2000.0,
    alert_threshold=0.8
)

# Check before routing
if not gateway.check_budget("pk_abc123"):
    raise BudgetExceededError()
```

### Rate Limit Management

```python
# Token bucket rate limiting
gateway.configure_rate_limits({
    "openai": {
        "requests_per_minute": 60,
        "tokens_per_minute": 90000
    },
    "anthropic": {
        "requests_per_minute": 40,
        "tokens_per_minute": 80000
    }
})
```

### Streaming Support

```python
# Unified streaming interface
for chunk in gateway.complete_stream(
    messages=messages,
    model="auto"
):
    print(chunk.content, end="")
```

## Provider Adapters

### Supported Providers

| Provider | Models | Streaming | Tools | Vision |
|----------|--------|-----------|-------|--------|
| OpenAI | GPT-4, GPT-4o, GPT-3.5 | ✅ | ✅ | ✅ |
| Anthropic | Claude 3 Opus/Sonnet/Haiku | ✅ | ✅ | ✅ |
| Google | Gemini Pro/Flash | ✅ | ✅ | ✅ |
| Azure OpenAI | GPT-4, GPT-3.5 | ✅ | ✅ | ✅ |
| AWS Bedrock | Claude, Llama, Titan | ✅ | ✅ | ✅ |
| Cohere | Command R/+ | ✅ | ✅ | ❌ |
| Ollama | Local models | ✅ | ✅ | ❌ |
| vLLM | Self-hosted | ✅ | ✅ | ✅ |

### Custom Provider

```python
from multi_ai_gateway.providers import BaseProvider

class CustomProvider(BaseProvider):
    def complete(self, messages, model, **kwargs):
        # Implement provider-specific logic
        return CompletionResponse(
            content=...,
            model=model,
            usage=TokenUsage(...)
        )

gateway.register_provider("custom", CustomProvider())
```

## Configuration

```yaml
# gateway.yaml
providers:
  openai:
    api_key: ${OPENAI_API_KEY}
    organization: ${OPENAI_ORG}
    default_model: gpt-4o
    models:
      gpt-4o:
        context_window: 128000
        cost_per_1k_input: 0.005
        cost_per_1k_output: 0.015
  
  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
    default_model: claude-3-sonnet
    models:
      claude-3-opus:
        context_window: 200000
        cost_per_1k_input: 0.015
        cost_per_1k_output: 0.075

routing:
  default_strategy: cost_optimized
  enabled_strategies:
    - cheapest
    - fastest
    - best_quality
  
  fallbacks:
    enabled: true
    max_retries: 3
    providers:
      - anthropic
      - openai
      - ollama

cache:
  enabled: true
  ttl_seconds: 300
  redis_url: redis://localhost:6379

observability:
  enabled: true
  log_requests: true
  log_responses: false
  metrics_endpoint: http://localhost:9090

limits:
  global:
    max_requests_per_minute: 1000
    max_tokens_per_minute: 100000
  
  per_key:
    default:
      daily_budget: 100
      monthly_budget: 2000
```

## Server Mode

```python
from multi_ai_gateway.server import GatewayServer

# Start as standalone server
server = GatewayServer(
    config="gateway.yaml",
    host="0.0.0.0",
    port=8080
)
server.run()
```

Now use standard OpenAI client pointing to your gateway:

```python
import openai

client = openai.OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="your-gateway-api-key"
)

# Routes internally to best available provider
response = client.chat.completions.create(
    model="gpt-4",  # Actually routes to available equivalent
    messages=[...]
)
```

## Smart Routing

```python
# Content-based routing
gateway.configure_router({
    "rules": [
        {
            "if": "task_type == 'coding'",
            "then": "prefer claude-3-sonnet"
        },
        {
            "if": "input_tokens > 100000",
            "then": "use claude-3-opus"
        },
        {
            "if": "budget_per_request < 0.01",
            "then": "use gpt-3.5-turbo"
        }
    ]
})
```

## Health Checks

```python
# Automatic health monitoring
gateway.enable_health_checks(
    interval_seconds=30,
    timeout_seconds=5
)

# Check provider health
health = gateway.health_check()
# {
#   "openai": {"status": "healthy", "latency_ms": 120},
#   "anthropic": {"status": "degraded", "latency_ms": 3000},
#   "ollama": {"status": "healthy", "latency_ms": 50}
# }
```

## Requirements

- Python 3.10+
- Provider SDKs as needed (openai, anthropic, google-generativeai)
- Redis (optional, for caching)
- Prometheus Client (optional, for metrics)

## License

MIT
