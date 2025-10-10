"""ReverseHasDeclaration
Parses reverse part-of sentences ("There are multiple engines for each rocket").
Normalizes to the canonical has direction: whole has→ part with cardinality.
"""
import os
import json
import re

from Project_Files.statement import Statement
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

class ReverseHasDeclaration(Statement):
    def __init__(self, model=None):
        super().__init__(model)
        self.model = model or "gpt-3.5-turbo"
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def setModel(self, model):
        self.model = model

    def translate(self, text):
        """Translate reverse part-of statements into deltas.
        Input variants get normalized; if not parseable returns an error list.
        """
        # --- Preprocessing ---
        text = re.sub(r"\bin (Graph|graph|Dataflow|Ontology|ontology)\b", "", text)
        text = re.sub(r"\bin the (Graph|graph|Dataflow|Ontology|ontology)\b", "", text)
        text = re.sub(r"\s+", " ", text).strip()

        print(f"🔄 Extracting PART-OF structure: {text}")

        system_prompt = """
You are a parser that extracts reverse 'part-of' relationships from English sentences like:

- "There are multiple engines for each rocket."
- "Several wings exist for every airplane."
- "There is one wheel for each tricycle."
- "At least one sensor is installed for every helmet."

From these, extract:

- part: the thing that exists multiple times (e.g., "engine", "sensor array")
- whole: the thing it belongs to (e.g., "rocket", "helmet", "parking garage")
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
- if the part is plural and no quantity is given → "+"

Formatting Instructions:
Return only the core noun phrase for both part and whole.
Strip leading determiners such as: "the", "a", "an", "this", "that", "each", "every".

Preserve meaningful multi-word expressions like:
- "sensor module"
- "parking garage"
- "control panel"
- "train car"

Response format (must match exactly):
{
  "part": "wheel",
  "whole": "tricycle",
  "cardinality": "1"
}

You must output relationships as WHOLE —has→ PART (with the extracted cardinality).

Examples (direction MUST be whole → part):
- "There are multiple engines for each rocket." →
  { "part": "engine", "whole": "rocket", "cardinality": "*" }  (edge: rocket —has(*)→ engine)

- "There is one printer for each tray." →
  { "part": "printer", "whole": "tray", "cardinality": "1" }  (edge: tray —has(1)→ printer)

Counterexample (do NOT do this):
- { "part": "tray", "whole": "printer", ... }  # WRONG direction for the sentence above

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

            required_keys = {"part", "whole", "cardinality"}
            if not required_keys.issubset(parsed.keys()):
                print("⚠️ Missing keys in parsed result:", parsed)
                return [{"error": "Incomplete structured response"}]

            return self.assemble(parsed)

        except Exception as e:
            print(f"❌ Failed to parse: {text}")
            print(f"❌ Exception: {e}")
            return [{"error": str(e)}]

    def assemble(self, parsed):
        """Assemble parsed dict into [add(part), add_edge(whole has→ part)]."""
        try:
            if "error" in parsed:
                return [{"error": parsed["error"]}]

            part = parsed["part"]
            whole = parsed["whole"]
            card = parsed["cardinality"]

            if not isinstance(part, str) or not isinstance(whole, str) or not isinstance(card, str):
                print("⚠️ Invalid field types in parsed:", parsed)
                return [{"error": "Invalid field types in parsed response"}]

            # Normalize direction to whole --has--> part per OWL modeling
            return [
                {
                    "update": "add",
                    "content": {
                        "node": part,
                        "annotations": []
                    }
                },
                {
                    "update": "add",
                    "content": {
                        "from_node": whole,
                        "to_node": part,
                        "label": "has",
                        "cardinality": card
                    }
                }
            ]
        except Exception as e:
            print(f"❌ Exception during assemble: {e}")
            print(f"❌ Parsed input was: {parsed}")
            return [{"error": f"Assembly failed: {e}"}]
