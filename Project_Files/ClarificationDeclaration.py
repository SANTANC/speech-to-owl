"""ClarificationDeclaration
Parses one-word responses to clarification prompts ("yes"/"no").
Produces a clarification delta that upstream code can route.
"""
from Project_Files.statement import Statement
import string


class ClarificationDeclaration(Statement):
    def __init__(self, model=None):
        super().__init__(model)

    def translate(self, text):
        """Normalize and validate a yes/no answer; returns a clarification delta."""
        normalized = text.strip().lower().translate(str.maketrans('', '', string.punctuation))
        if normalized not in {"yes", "no"}:
            raise ValueError(f"ClarificationDeclaration expects 'yes' or 'no', got: {text}")

        return [
            {
            "update": "clarification",
            "content": {
                        "response": normalized
            },
            "graph": "unknown"
            }
            ]

