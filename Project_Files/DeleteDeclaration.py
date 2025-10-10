"""DeleteDeclaration
Parses deletion requests like "Delete the node 'volcano'".
Produces a single delta: {"update":"delete","content":{"id":"..."}}.
"""
import os
import json
import re
from Project_Files.statement import Statement
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class DeleteDeclaration(Statement):
    def __init__(self, model=None):
        super().__init__(model)
        self.model = model or "gpt-3.5-turbo"
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def setModel(self, model):
        self.model = model

    def translate(self, text):
        """Translate delete statements into a single delete delta or an error."""
        text = re.sub(r"\s+", " ", text).strip()
        print(f"🗑️ Extracting DELETE instruction: {text}")

        system_prompt = """
    You are a parser that extracts DELETE instructions from simple English sentences like:
    
    - "Delete the node 'volcano'."
    - "Remove 'sensor module'."
    - "Delete the entity called 'kettle'."
    - "Please remove the concept 'satellite'."
    
    From these, extract:
    
    - id: the name of the node/entity/concept to delete
    
    💡 Formatting Rules:
    - Strip quotes if present
    - Strip determiners like "the", "a", "this", "that"
    - Preserve multi-word phrases like "sensor module" or "control panel"
    
    ✅ Response format:
    {
      "id": "volcano"
    }
    
    ❌ If the sentence does not describe a deletion, return:
    { "error": "Could not extract delete instruction" }
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

            return self.assemble(parsed)

        except Exception as e:
            print(f"❌ DeleteDeclaration failed: {e}")
            return [{"error": str(e)}]


    def assemble(self, parsed):
        """Assemble parsed dict into a delete delta (id must be a string)."""
        try:
            if "error" in parsed:
                return [{"error": parsed["error"]}]

            target_id = parsed["id"]
            if not isinstance(target_id, str):
                return [{"error": "Invalid ID format"}]

            return [{
                "update": "delete",
                "content": {
                    "id": target_id
                }
            }]
        except Exception as e:
            print(f"❌ Exception during delete assemble: {e}")
            return [{"error": f"Assembly failed: {e}"}]
