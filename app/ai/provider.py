from abc import ABC, abstractmethod
from typing import Any, Dict
from app.ai.models import AIAnalysisResponse


class AIProvider(ABC):
    """
    Abstract Interface for AI Incident Reasoning Providers.
    Allows seamlessly swapping Gemini with OpenAI, Ollama, or local models.
    """

    @abstractmethod
    def analyze(self, evidence: Dict[str, Any], incident_id: str = "") -> AIAnalysisResponse:
        """
        Analyze sanitized incident evidence and return structured AI response.
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if provider is configured and available.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Name of the AI Provider (e.g. 'gemini', 'openai').
        """
        pass
