"""RenameDeclaration
Parses rename requests like "Rename Paris to Paris, France".
Produces a rename delta consumed by OwlBuilder to relabel classes.
"""
import os
import json
import re

from Project_Files.statement import Statement
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

class RenameDeclaration(Statement):
    def __init__(self, model=None):
        super().__init__(model)
        self.model = model or "gpt-3.5-turbo"
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def setModel(self, model):
        self.model = model

    def translate(self, text):
        """Translate rename statements into a single delta or an error."""
        text = re.sub(r"\s+", " ", text).strip()
        print(f"✏️ Extracting RENAME instruction: {text}")

        system_prompt = """
You are a parser that extracts RENAME instructions from simple English sentences like:

- "Rename Paris to Paris, France."
- "Change the name of forest to Dense Forest."
- "Please rename sensor module as temperature sensor."
- "Update the label 'volcano' to 'volcanic mountain'."

From these, extract:

- from: the current name
- to: the new name

💡 Formatting Rules:
- Strip any quotes or determiners (like "the", "a", "this", "that", "entity", etc.)
- Preserve full multi-word expressions (e.g., "sensor module", "dense forest")
- The "from" and "to" should be meaningful, standalone names

✅ Response format:
{
  "from": "Paris",
  "to": "Paris, France"
}

❌ If the sentence does not describe a renaming, return:
{ "error": "Could not extract rename instruction" }
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

            required_keys = {"from", "to"}
            if not required_keys.issubset(parsed.keys()):
                print("⚠️ Missing keys in parsed result:", parsed)
                return [{"error": "Incomplete structured response"}]

            return self.assemble(parsed)

        except Exception as e:
            print(f"❌ Failed to parse: {text}")
            print(f"❌ Exception: {e}")
            return [{"error": str(e)}]

    def assemble(self, parsed):
        """Assemble parsed dict into a rename delta (from/to must be strings)."""
        try:
            if "error" in parsed:
                return [{"error": parsed["error"]}]

            old_name = parsed["from"]
            new_name = parsed["to"]

            if not isinstance(old_name, str) or not isinstance(new_name, str):
                return [{"error": "Invalid rename input types"}]

            return [{
                "update": "rename",
                "content": {
                    "from": old_name,
                    "to": new_name
                }
            }]
        except Exception as e:
            print(f"❌ Exception during rename assemble: {e}")
            print(f"❌ Parsed input was: {parsed}")
            return [{"error": f"Assembly failed: {e}"}]
