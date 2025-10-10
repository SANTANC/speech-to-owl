import openai
from typing import Dict

# Explicit, robust registry: import declarations as package modules
from Project_Files.NodeDeclaration import NodeDeclaration
from Project_Files.HasDeclaration import HasDeclaration
from Project_Files.ReverseHasDeclaration import ReverseHasDeclaration
from Project_Files.AnnotatedEdgeDeclaration import AnnotatedEdgeDeclaration
from Project_Files.DeleteDeclaration import DeleteDeclaration
from Project_Files.RenameDeclaration import RenameDeclaration
from Project_Files.UndoDeclaration import UndoDeclaration
from Project_Files.ClarificationDeclaration import ClarificationDeclaration


class ParserDecider:
    def __init__(self, model="gpt-3.5-turbo"):
        self.model = model
        self.declarators: Dict[str, object] = self.load_declarators()
        self.system_prompt = self.build_system_prompt()

    def load_declarators(self) -> Dict[str, object]:
        # Build a stable registry of declarators
        loaded = {
            "NodeDeclaration": NodeDeclaration(model=self.model),
            "HasDeclaration": HasDeclaration(model=self.model),
            "ReverseHasDeclaration": ReverseHasDeclaration(model=self.model),
            "AnnotatedEdgeDeclaration": AnnotatedEdgeDeclaration(model=self.model),
            "DeleteDeclaration": DeleteDeclaration(model=self.model),
            "RenameDeclaration": RenameDeclaration(model=self.model),
            "UndoDeclaration": UndoDeclaration(model=self.model),
            "ClarificationDeclaration": ClarificationDeclaration(model=self.model),
        }
        print(f"📦 Loaded declarators: {list(loaded.keys())}")
        return loaded

    def build_system_prompt(self) -> str:
        prompt = "You are a classifier that labels sentences for a knowledge graph parser.\n"
        prompt += "Label each sentence as one of the following:\n"

        for label in self.declarators:
            prompt += f"- {label}\n"

        prompt += "- None (if the sentence is unrelated or can't be parsed)\n\n"
        prompt += """Examples:
        - "I have a node called computer." → NodeDeclaration
        - "Add donkey to the graph." → NodeDeclaration
        - "There is an entity called volcano." → NodeDeclaration
        - "Create a gyroscope sensor in the dataflow graph." → NodeDeclaration
        - "Insert a camera object into the ontology graph." → NodeDeclaration
    
        - "Remove the node called horse." → DeleteDeclaration
        - "Delete the volcano node." → DeleteDeclaration
        - "Erase the propeller entity in the graph." → DeleteDeclaration
        - "Delete edge between light and battery." → DeleteDeclaration
        - "Remove relationship between frying pan and stove." → DeleteDeclaration
        - "Remove the link between the sensor and the car." → DeleteDeclaration
        - "Delete the connection between gyroscope and processor." → DeleteDeclaration
        - "Delete the Printer node from the ontology graph." → DeleteDeclaration
    
        - "Undo last command." → UndoDeclaration
        - "Undo that." → UndoDeclaration
        - "Undo that node." → UndoDeclaration
        - "Revert the previous step in the graph." → UndoDeclaration
    
        - "Parking Garage has an entrance." → HasDeclaration
        - "The car has wheels." → HasDeclaration
        - "A classroom has multiple desks." → HasDeclaration
        - "Each robot has a sensor module." → HasDeclaration
    
        - "There are multiple engines for each rocket." → ReverseHasDeclaration
        - "Several pages exist for every book." → ReverseHasDeclaration
        - "One battery is used for every device." → ReverseHasDeclaration
        - "There are many seats for each train car in the ontology graph." → ReverseHasDeclaration
    
        - "Rename Paris to Paris, France." → RenameDeclaration
        - "Change the name of forest to Dense Forest." → RenameDeclaration
        - "Please rename sensor module as temperature sensor." → RenameDeclaration
        - "Update the label volcano to volcanic mountain." → RenameDeclaration
        
        - "Yes" → ClarificationDeclaration
        - "No" → ClarificationDeclaration
        
        - "A printer is closeby to another printer." → AnnotatedEdgeDeclaration
        - "The server is linked to the firewall." → AnnotatedEdgeDeclaration
        - "The turbine connects with the generator." → AnnotatedEdgeDeclaration
        - "A camera is mounted beside another camera." → AnnotatedEdgeDeclaration
        - "One robot is adjacent to another robot." → AnnotatedEdgeDeclaration
        - "Printer has the relationship closeby with another printer." → AnnotatedEdgeDeclaration
    
        - "P-I-E-I-O." → None
        - "Happy Gertie Day!" → None
    
    Only return one of: """ + ", ".join(list(self.declarators.keys()) + ["None"]) + "."
        return prompt



    def parse(self, sentence: str, return_with_parser=False):
        lowered = sentence.lower()

        # --- Rule-based routing ---
        if any(kw in lowered for kw in ["has", "owns", "includes", "consists of", "contains"]):
            label = "HasDeclaration"

        elif any(kw in lowered for kw in ["add", "create", "define", "node", "entity"]):
            label = "NodeDeclaration"

        elif (
                any(kw in lowered for kw in ["for each", "for every", "per", "exists for", "exist for"])
                and any(quant in lowered for quant in ["multiple", "several", "many", "one", "two", "three", "four", "five", "a ", "an "])
        ):
            label = "ReverseHasDeclaration"

        else:
            # --- Fallback to LLM classification ---
            user_prompt = f'Sentence: "{sentence}"\nLabel:'
            client = openai.OpenAI()
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
            )
            label = response.choices[0].message.content.strip()

        print(f"📎 Selected label: {label}")

        parser = self.declarators.get(label)
        result = None

        if parser:
            result = parser.translate(sentence)
            print(f"📤 Parser output: {result}")
        else:
            print(f"⚠️ No parser found for label: {label}")

        # Determine validity
        is_valid = isinstance(result, list) and "error" not in result[0]

        if return_with_parser:
            return {
                "label": label if is_valid else "None",
                "result": result
            }

        return result
