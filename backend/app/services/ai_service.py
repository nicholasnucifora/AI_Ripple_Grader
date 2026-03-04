import anthropic
from app.core.config import settings


class AIService:
    """Wraps the Anthropic client. All AI grading logic lives here."""

    def __init__(self):
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._model = settings.anthropic_model

    def grade_submission(
        self,
        sections: list[str],
        rubric: dict,
        moderations: list[dict],
        strictness: str,
    ) -> dict:
        """
        Grade student content sections against a rubric using Claude Tool Use.
        Returns: {"criterion_grades": [...], "overall_feedback": "..."}
        """
        strictness_instructions = {
            "lenient": "err on the side of generosity when evidence is partial",
            "standard": "apply criteria as written",
            "strict": "only award a level if all descriptors are fully demonstrated",
        }
        strictness_note = strictness_instructions.get(strictness, "apply criteria as written")

        grade_tool = {
            "name": "submit_grade",
            "description": (
                "Submit the complete grading result for this student submission. "
                "Call this tool exactly once with grades for every criterion."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "criterion_grades": {
                        "type": "array",
                        "description": "One entry per rubric criterion.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "criterion_id": {
                                    "type": "string",
                                    "description": "The criterion id from the rubric.",
                                },
                                "criterion_name": {
                                    "type": "string",
                                    "description": "The criterion name.",
                                },
                                "level_id": {
                                    "type": "string",
                                    "description": "The id of the awarded performance level.",
                                },
                                "level_title": {
                                    "type": "string",
                                    "description": "The title of the awarded performance level.",
                                },
                                "points_awarded": {
                                    "type": "number",
                                    "description": "Points awarded for this criterion.",
                                },
                                "feedback": {
                                    "type": "string",
                                    "description": "Brief justification for this grade.",
                                },
                            },
                            "required": [
                                "criterion_id",
                                "criterion_name",
                                "level_id",
                                "level_title",
                                "points_awarded",
                                "feedback",
                            ],
                        },
                    },
                    "overall_feedback": {
                        "type": "string",
                        "description": "Overall feedback for the student.",
                    },
                },
                "required": ["criterion_grades", "overall_feedback"],
            },
        }

        rubric_md = self.format_rubric_to_markdown(rubric)

        content_block = "\n\n".join(
            f"### Section {i + 1}\n{s}" for i, s in enumerate(sections)
        )

        user_message = (
            f"Grade the following student submission against the rubric. "
            f"Strictness instruction: {strictness_note}.\n\n"
            f"{rubric_md}\n\n"
            f"## Student Submission\n\n{content_block}"
        )

        if moderations:
            mod_lines = "\n".join(
                f"- [{m.get('role', 'reviewer')}]: {m.get('comment', '')}"
                for m in moderations
                if m.get("comment", "").strip()
            )
            if mod_lines:
                user_message += (
                    "\n\n## Peer reviews for context (do not grade the reviewer):\n"
                    + mod_lines
                )

        response = self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            tools=[grade_tool],
            tool_choice={"type": "tool", "name": "submit_grade"},
            messages=[{"role": "user", "content": user_message}],
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "submit_grade":
                return block.input

        raise ValueError("Claude did not return a grade tool call")

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
