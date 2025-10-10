"""NodeDeclaration
Parses simple imperative sentences that request creating a node/class.
Returns normalized deltas that OwlBuilder can consume to create owl:Class.
Primary path uses OpenAI for robust extraction; falls back to a safe regex.
"""
import os
import json
import re
from Project_Files.statement import Statement
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class NodeDeclaration(Statement):
    def __init__(self, model=None):
        super().__init__(model)
        self.model = model or "gpt-3.5-turbo"
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Pre-compile a SAFE, readable fallback regex (no unbalanced groups)
        self._fallback_pattern = re.compile(
            r"""
            \b(?:add|create|define|insert|make|new)\s+   # command
            (?P<node>                                    # start node capture
                (?:
                    (?!\s+(?:to|in|into)\s+(?:the\s+)?   # don't consume the trailing graph phrase
                        (?:ontology|dataflow)\s+graph\b)
                    .
                )+?                                      # minimal, any char
            )                                            # end node
            (?:\s+(?:to|in|into)\s+(?:the\s+)?(?:ontology|dataflow)\s+graph)?  # optional graph phrase
            [\s.]*$                                      # end
            """,
            re.IGNORECASE | re.VERBOSE
        )

    def setModel(self, model):
        self.model = model

    def translate(self, text):
        """Translate a natural-language node creation into deltas.
        Input: e.g., "Add a node called volcano."
        Output: [ {"update":"add","content":{"node":"volcano","annotations":[...]}} ] or error list.
        """
        # --- Minimal preprocessing: remove graph-locator boilerplate only (do NOT alter nouns) ---
        text = re.sub(r"\bin (Graph|graph|Dataflow|Ontology|ontology)\b", "", text)
        text = re.sub(r"\bin the (Graph|graph|Dataflow|Ontology|ontology)\b", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        print(f"🔍 Extracting node declaration: {text}")

        # --- 1) LLM as primary path ---
        system_prompt = """
You are a parser that extracts node declarations from instructions like:

- "Add a node called volcano."
- "Insert a node named satellite."
- "Create a node labeled mountain."
- "Add a sensor named gyroscope."
- "Create a device called thermometer."
- "Add car"

From each sentence, extract:

- node: the name of the node to create (e.g., "volcano", "satellite", "sensor package")
- annotations: a list of tags like "sensor", "device", "object" (or empty if not applicable)

Formatting Instructions:
- Return only the core noun phrase for the node name.
- Strip leading determiners such as: "the", "a", "an", "this", "that", "each", "every".
- Preserve multi-word concepts (e.g., "parking garage", "sensor module").

STRICT RULES:
- Do NOT fix typos or rename the node. If the input says "pinter", the node must be "pinter".
- If the sentence is not a node creation, return the error format.

Response format:
{
  "node": "gyroscope",
  "annotations": ["sensor"]
}

Or, if there are no annotations:
{
  "node": "volcano",
  "annotations": []
}

If the sentence does not describe a valid node creation, return:
{ "error": "Could not extract node" }
""".strip()

        parsed = None
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0
            )
            reply = (response.choices[0].message.content or "").strip()

            # Try direct JSON first
            try:
                parsed = json.loads(reply)
            except json.JSONDecodeError:
                # Try to extract the first JSON object if the model added extra text
                m = re.search(r'\{.*\}', reply, flags=re.DOTALL)
                if m:
                    parsed = json.loads(m.group(0))
        except Exception as e:
            print(f"❌ NodeDeclaration LLM call failed: {e}")

        if isinstance(parsed, dict) and "error" not in parsed:
            result = self.assemble(parsed)
            if isinstance(result, list) and result and "error" not in result[0]:
                print(f"📤 Parser output (LLM): {result}")
                return result

        # --- 2) Regex fallback if LLM failed or returned error/invalid ---
        # Expanded fallback patterns to catch many natural phrasings
        patterns = [
            self._fallback_pattern,
            re.compile(r"^(?:and\s+)?(?:add|create|make|define|insert)\s+(?:a|an|the\s+)?(?:(?:class|node|entity|object|thing|concept|item)\s+)?(?P<node>.+?)[\s.]*$", re.IGNORECASE),
            re.compile(r"^(?:and\s+)?i\s+have\s+(?:a|an|the\s+)?(?:class|node|entity|object|thing|concept|item)\s+(?P<node>.+?)[\s.]*$", re.IGNORECASE),
            re.compile(r"^(?:and\s+)?there\s+(?:is|\'s)\s+(?:a|an\s+)?(?:class|node|entity|object|thing|concept|item)\s+(?P<node>.+?)[\s.]*$", re.IGNORECASE),
            re.compile(r"^(?:class|node|entity|object|thing|concept|item)\s+(?P<node>.+?)[\s.]*$", re.IGNORECASE),
        ]
        m = None
        for pat in patterns:
            try:
                m = pat.search(text)
            except re.error as e:
                print(f"⚠️ Regex error in fallback pattern: {e}")
                continue
            if m:
                break

        if m:
            node = m.group("node").strip()
            result = [{
                "update": "add",
                "content": {"node": node, "annotations": []}
            }]
            print(f"📤 Parser output (regex fallback): {result}")
            return result

        # --- 3) Nothing matched ---
        print("⚠️ NodeDeclaration: could not extract node (LLM + regex failed)")
        return [{"error": "Could not extract node"}]

    def assemble(self, parsed):
        """Assemble parsed dict into a normalized delta list.
        Ensures node is a non-empty string and annotations is a list.
        """
        try:
            if "error" in parsed:
                return [{"error": parsed["error"]}]

            node = parsed.get("node")
            annotations = parsed.get("annotations", [])

            if not isinstance(node, str) or not node.strip() or not isinstance(annotations, list):
                return [{"error": "Invalid node format"}]

            # Direct add; ontology graph will handle any downstream clarifications.
            return [{
                "update": "add",
                "content": {
                    "node": node.strip(),
                    "annotations": annotations
                }
            }]
        except Exception as e:
            print(f"❌ Exception during assemble: {e}")
            return [{"error": f"Assembly failed: {e}"}]
