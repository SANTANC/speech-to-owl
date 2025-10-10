import os
import json
import re
from Project_Files.statement import Statement
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class UndoDeclaration(Statement):
    def __init__(self, model=None):
        super().__init__(model)
        self.model = model or "gpt-3.5-turbo"
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def setModel(self, model):
        self.model = model

    def translate(self, text):
        text = re.sub(r"\s+", " ", text).strip()
        print(f"↩️ Extracting UNDO instruction: {text}")

        system_prompt = """
You are a parser that extracts undo instructions from sentences like:

- "Undo the last action."
- "Revert the previous step."
- "Go back one change."
- "Undo."

✅ If the sentence means to undo the last operation, respond with:
{
  "update": "undo"
}

❌ If it does not clearly request an undo operation, respond with:
{ "error": "Could not extract undo instruction" }
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

            if "error" in parsed:
                return [{"error": parsed["error"]}]
            if parsed.get("update") != "undo":
                return [{"error": "Unexpected format"}]

            return [parsed]

        except Exception as e:
            print(f"❌ UndoDeclaration failed: {e}")
            return [{"error": str(e)}]
