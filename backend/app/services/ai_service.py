import anthropic
from app.core.config import settings


class AIService:
    """Wraps the Anthropic client. All AI grading logic lives here."""

    def __init__(self):
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._model = settings.anthropic_model

    def grade_submission(self, submission_text: str, rubric: str) -> dict:
        """
        Grade a student submission against a rubric.
        Returns a dict with at least: { "score": ..., "feedback": ... }
        """
        # TODO: implement grading prompt + response parsing
        raise NotImplementedError


ai_service = AIService()
