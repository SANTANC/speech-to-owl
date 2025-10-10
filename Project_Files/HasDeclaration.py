"""HasDeclaration
Parses sentences of the form "X has Y" with optional cardinalities.
Produces deltas to add object class and an edge (X has→ Y) with cardinality.
"""
import os
import json
import re

from Project_Files.statement import Statement
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

class HasDeclaration(Statement):
    def __init__(self, model=None):
        super().__init__(model)
        self.model = model or "gpt-3.5-turbo"
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def setModel(self, model):
        self.model = model

    def translate(self, text):
        """Translate 'has' statements into deltas with cardinality mapping.
        Returns a list: [add(object), add_edge(subject has→ object)].
        """

        # --- Preprocessing to remove "in Graph ..." or "in Dataflow ..." ---
        text = re.sub(r"\bin (Graph|graph|Dataflow|Ontology|ontology)\b", "", text)
        text = re.sub(r"\bin the (Graph|graph|Dataflow|Ontology|ontology)\b", "", text)
        text = re.sub(r"\s+", " ", text).strip()

        print(f"🔍 Extracting HAS structure: {text}")

        system_prompt = """
You are a parser that extracts 'has' relationships from simple English sentences like:

- "The car has wheels."
- "A robot has sensors."
- "The printer has a toner cartridge."
- "A drone has one camera."
- "The subject has (cardinality phrase) object."

From such sentences, extract:

- subject: the thing that has something (e.g., "car", "printer", "parking garage")
- object: the thing being had (e.g., "wheels", "toner cartridge", "sensor array")
- cardinality: a single string token based on the rules below

Cardinality rules (return as string):
- "a", "an", "one" → "1"
- "two" → "2"
- "three" → "3"
- "four" → "4"
- "five" → "5"
- "six" → "6"
- "seven" → "7"
- "eight" → "8"
- "nine" → "9"
- "ten" → "10"
- "several", "multiple", "many" → "*"
- "at least one" → "+"
- if the object is plural and no quantity is given → "+"

Formatting Instructions:
Return only the core noun phrase for both subject and object.
Strip leading determiners such as: "the", "a", "an", "this", "that", "each", "every".

Preserve meaningful multi-word expressions like:
- "sensor module"
- "parking garage"
- "control panel"
- "mobile robot"

Response format (must match exactly):
{
  "subject": "car",
  "object": "wheels",
  "cardinality": "4"
}

If the sentence cannot be parsed, return:
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

            required_keys = {"subject", "object", "cardinality"}
            if not required_keys.issubset(parsed.keys()):
                print("⚠️ Missing keys in parsed result:", parsed)
                return [{"error": "Incomplete structured response"}]

            return self.assemble(parsed)

        except Exception as e:
            print(f"❌ Failed to parse: {text}")
            print(f"❌ Exception: {e}")
            return [{"error": str(e)}]

    def assemble(self, parsed):
        """Assemble parsed fields into normalized deltas for OwlBuilder.
        Validates that subject, object, and cardinality are strings.
        """
        try:
            if "error" in parsed:
                return [{"error": parsed["error"]}]

            subj = parsed["subject"]
            obj = parsed["object"]
            card = parsed["cardinality"]

            if not isinstance(subj, str) or not isinstance(obj, str) or not isinstance(card, str):
                print("⚠️ Invalid field types in parsed:", parsed)
                return [{"error": "Invalid field types in parsed response"}]

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
                        "label": "has",
                        "cardinality": card
                    }
                }
            ]
        except Exception as e:
            print(f"❌ Exception during assemble: {e}")
            print(f"❌ Parsed input was: {parsed}")
            return [{"error": f"Assembly failed: {e}"}]
