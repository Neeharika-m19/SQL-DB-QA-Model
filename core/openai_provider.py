# core/llm/openai_provider.py

import openai
from .base import LLMProvider
from typing import List
from core.encryption_util import decrypt_api_key
from db.model import APIKey, User
from sqlmodel import Session, select


class OpenAIProvider(LLMProvider):
    def __init__(self, session: Session, user_id: int):
        self.session = session
        self.user_id = user_id

    def get_api_key(self) -> str:
        user = self.session.get(User, self.user_id)
        if not user or not user.fernet_key:
            raise Exception("User or Fernet key not found.")

        key_entry = self.session.exec(
            select(APIKey).where(APIKey.user_id == self.user_id, APIKey.provider == "openai")
        ).first()

        if not key_entry:
            raise Exception("API key for OpenAI not found.")

        return decrypt_api_key(key_entry.encrypted_key, user.fernet_key)

    def get_available_models(self) -> List[str]:
        api_key = self.get_api_key()
        openai.api_key = api_key
        try:
            response = openai.models.list()
            return [model.id for model in response.data]
        except Exception as e:
            raise Exception(f"Error fetching OpenAI models: {e}")

    def generate_sql(self, question: str, schema: str, model: str, user_id: int) -> str:
        api_key = self.get_api_key()
        # Replace this with actual OpenAI call logic if needed
        return f"-- SQL from OpenAI ({model}) for question: {question} using key: {api_key[:6]}****"
