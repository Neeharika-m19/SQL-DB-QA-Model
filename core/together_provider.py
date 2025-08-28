# core/llm/together_provider.py

import requests
from .base import LLMProvider
from typing import List
from core.encryption_util import decrypt_api_key
from db.model import APIKey, User
from sqlmodel import Session, select
from core.db import get_session


class TogetherAIProvider(LLMProvider):
    def get_api_key(self, session: Session, user_id: int) -> str:
        user = session.get(User, user_id)
        if not user or not user.fernet_key:
            raise Exception("User or Fernet key not found.")

        key_entry = session.exec(
            select(APIKey).where(APIKey.user_id == user_id, APIKey.provider == "together")
        ).first()

        if not key_entry:
            raise Exception("API key for Together AI not found.")

        return decrypt_api_key(key_entry.encrypted_key, user.fernet_key)

    def get_available_models(self) -> List[str]:
        session = get_session()
        with session:
            api_key = self.get_api_key(session, self.user_id)
            headers = {"Authorization": f"Bearer {api_key}"}
            try:
                response = requests.get("https://api.together.xyz/models", headers=headers)
                response.raise_for_status()
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
            except Exception as e:
                raise Exception(f"Error fetching Together AI models: {e}")

    def generate_sql(self, question: str, schema: str, model: str, user_id: int) -> str:
        session = get_session()
        with session:
            api_key = self.get_api_key(session, user_id)
            # Replace this with actual Together API completion logic
            return f"-- SQL from Together AI ({model}) for question: {question} using key: {api_key[:6]}****"

    def __init__(self, session: Session, user_id: int):
        self.session = session
        self.user_id = user_id
