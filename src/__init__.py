"""Multi-AI Gateway - Unified LLM routing with failover and load balancing."""

from .gateway import Gateway
from .routing import RoutingStrategy, Router
from .providers import BaseProvider, OpenAIProvider, AnthropicProvider
from .models import CompletionRequest, CompletionResponse, RoutingConfig

__version__ = "0.1.0"
__all__ = [
    "Gateway",
    "RoutingStrategy",
    "Router",
    "BaseProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "CompletionRequest",
    "CompletionResponse",
    "RoutingConfig",
]
