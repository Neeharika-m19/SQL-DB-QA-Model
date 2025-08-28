from abc import ABC, abstractmethod
from typing import List

class LLMProvider(ABC):
    @abstractmethod
    def get_available_models(self) -> List[str]:
        pass

    @abstractmethod
    def generate_sql(self, question: str, schema: str, model: str) -> str:
        pass
