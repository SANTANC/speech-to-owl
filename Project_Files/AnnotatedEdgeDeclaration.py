"""AnnotatedEdgeDeclaration
Parses labeled relationships like "A communicates with B" or "is connected to".
Produces deltas to add the object class and add an edge with the label.
"""
import os
import json
import re

from Project_Files.statement import Statement
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

class AnnotatedEdgeDeclaration(Statement):
    def __init__(self, model=None):
        super().__init__(model)
        self.model = model or "gpt-3.5-turbo"
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def setModel(self, model):
        self.model = model

    def translate(self, text):
        """Translate labeled edge statements into deltas for OwlBuilder."""
        text = re.sub(r"\bin (Graph|graph|Dataflow|Ontology|ontology)\b", "", text)
        text = re.sub(r"\bin the (Graph|graph|Dataflow|Ontology|ontology)\b", "", text)
        text = re.sub(r"\s+", " ", text).strip()

        print(f"🔍 Extracting annotated edge structure: {text}")

        system_prompt = """
You are a parser that extracts labeled relationships between entities from simple English sentences.

Examples:
- "A printer has the relationship closeby with another printer."
- "A drone is connected to a control panel."
- "Each sensor communicates with the hub."

Extract:
- subject: the first entity
- object: the second entity
- label: the relationship type (e.g., "connected", "closeby", "communicates")
- cardinality: see rules below

Cardinality rules:
- "a", "an", "one" → "1"
- numbers spelled out → corresponding number
- "several", "many", "multiple" → "*"
- "at least one" → "+"
- plural object with no number → "+"

Response format:
{
  "subject": "printer",
  "object": "printer",
  "label": "closeby",
  "cardinality": "1"
}

If parsing fails, return:
{ "error": "Could not extract parts" }
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0
            )
            reply = response.choices[0].message.content.strip()
            parsed = json.loads(reply)

            if not isinstance(parsed, dict):
                print("⚠️ Parsed result is not a dict:", parsed)
                return [{"error": "Invalid structured response"}]

            required_keys = {"subject", "object", "label", "cardinality"}
            if not required_keys.issubset(parsed.keys()):
                print("⚠️ Missing keys in parsed result:", parsed)
                return [{"error": "Incomplete structured response"}]

            return self.assemble(parsed)

        except Exception as e:
            print(f"❌ Failed to parse: {text}")
            print(f"❌ Exception: {e}")
            return [{"error": str(e)}]

    def assemble(self, parsed):
        """Assemble parsed dict into [add(object), add_edge(subject label→ object)]."""
        try:
            if "error" in parsed:
                return [{"error": parsed["error"]}]

            subj = parsed["subject"]
            obj = parsed["object"]
            label = parsed["label"]
            card = parsed["cardinality"]

            if not all(isinstance(field, str) for field in [subj, obj, label, card]):
                print("⚠️ Invalid field types in parsed:", parsed)
                return [{"error": "Invalid field types in parsed response"}]

            # For OWL class axioms, we only need class and property restriction.
            return [
                {
                    "update": "add",
                    "content": {
                        "node": obj,
                        "annotations": []
                    }
                },
                {
                    "update": "add",
                    "content": {
                        "from_node": subj,
                        "to_node": obj,
                        "label": label,
                        "cardinality": card
                    }
                }
            ]
        except Exception as e:
            print(f"❌ Exception during assemble: {e}")
            print(f"❌ Parsed input was: {parsed}")
            return [{"error": f"Assembly failed: {e}"}]
