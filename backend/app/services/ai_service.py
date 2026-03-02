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

    def extract_rubric(self, markdown: str) -> dict:
        """
        Use Anthropic Tool Use to extract a structured rubric from Markdown text.
        Returns a dict matching RubricSchema.
        Raises ValueError on failure.
        """
        rubric_tool = {
            "name": "submit_rubric",
            "description": (
                "Submit a fully structured grading rubric extracted from the provided document. "
                "Call this tool exactly once with the complete rubric."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The name or title of the rubric/assessment.",
                    },
                    "criteria": {
                        "type": "array",
                        "description": "List of grading criteria.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {
                                    "type": "string",
                                    "description": "Unique identifier (e.g. 'c1', 'c2').",
                                },
                                "name": {
                                    "type": "string",
                                    "description": "Name of this criterion.",
                                },
                                "weight_percentage": {
                                    "type": "number",
                                    "description": "Percentage weight of this criterion (0-100).",
                                },
                                "levels": {
                                    "type": "array",
                                    "description": "Performance levels for this criterion, from highest to lowest.",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "id": {
                                                "type": "string",
                                                "description": "Unique level identifier (e.g. 'c1l1').",
                                            },
                                            "title": {
                                                "type": "string",
                                                "description": "Level label (e.g. 'Excellent', 'Pass').",
                                            },
                                            "points": {
                                                "type": "number",
                                                "description": "Points awarded for this level.",
                                            },
                                            "description": {
                                                "type": "string",
                                                "description": "What a student must demonstrate to achieve this level.",
                                            },
                                        },
                                        "required": ["id", "title", "points", "description"],
                                    },
                                },
                            },
                            "required": ["id", "name", "weight_percentage", "levels"],
                        },
                    },
                },
                "required": ["title", "criteria"],
            },
        }

        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            tools=[rubric_tool],
            tool_choice={"type": "tool", "name": "submit_rubric"},
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Extract a structured grading rubric from the following document. "
                        "Identify all criteria, their weights, and performance levels with point values.\n\n"
                        f"---\n{markdown}\n---"
                    ),
                }
            ],
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "submit_rubric":
                return block.input

        raise ValueError("Claude did not return a rubric tool call")

    def format_rubric_to_markdown(self, rubric: dict) -> str:
        """
        Deterministic Markdown formatter for a rubric dict.
        Criteria sorted by name, levels sorted by points descending.
        Produces consistent output suitable as a static prompt-caching prefix.
        """
        lines = [f"# {rubric['title']}", "", "## Criteria", ""]
        sorted_criteria = sorted(rubric["criteria"], key=lambda c: c["name"])
        for criterion in sorted_criteria:
            lines.append(f"### {criterion['name']} ({criterion['weight_percentage']}%)")
            lines.append("| Level | Points | Description |")
            lines.append("|-------|--------|-------------|")
            sorted_levels = sorted(criterion["levels"], key=lambda l: l["points"], reverse=True)
            for level in sorted_levels:
                lines.append(f"| {level['title']} | {level['points']} | {level['description']} |")
            lines.append("")
        return "\n".join(lines)


ai_service = AIService()
