# core/llm/factory.py

from .openai_provider import OpenAIProvider
from .together_provider import TogetherAIProvider
from sqlmodel import Session
from .base import LLMProvider


def get_llm_provider(provider_name: str, session: Session, user_id: int) -> LLMProvider:
    provider_name = provider_name.lower()

    if provider_name == "openai":
        return OpenAIProvider(session, user_id)
    elif provider_name == "together":
        return TogetherAIProvider(session, user_id)
    else:
        raise ValueError(f"Unsupported provider: {provider_name}")
