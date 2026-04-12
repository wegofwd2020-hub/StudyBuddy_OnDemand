"""
pipeline/providers

LLM provider abstraction layer for the StudyBuddy content pipeline.

Usage:
    from pipeline.providers import get_provider

    provider = get_provider("anthropic", config)
    text, in_tok, out_tok = provider.generate(prompt)
"""

from pipeline.providers.registry import get_provider, list_providers

__all__ = ["get_provider", "list_providers"]
