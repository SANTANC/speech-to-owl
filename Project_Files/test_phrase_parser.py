"""Parser unit tests

These tests validate the behavior of the Declaration classes that parse
natural-language sentences into normalized deltas (updates) consumed by
OwlBuilder. They focus on structure and direction rather than LLM internals.
"""
import unittest
from HasDeclaration import HasDeclaration
from NodeDeclaration import NodeDeclaration
from ReverseHasDeclaration import ReverseHasDeclaration
from DeleteDeclaration import DeleteDeclaration
from UndoDeclaration import UndoDeclaration


class TestHasDeclaration(unittest.TestCase):
    def setUp(self):
        self.parser = HasDeclaration()

    def test_has_relationships(self):
        cases = [
            ("The car has four doors.", "car", "doors", "4"),
            ("A server has several drives.", "server", "drives", "*"),
            ("A kettle has a handle.", "kettle", "handle", "1"),
            ("This building has floors.", "building", "floors", "+")
        ]
        for sentence, subj, obj, card in cases:
            with self.subTest(sentence=sentence):
                result = self.parser.translate(sentence)
                flat = [item for sub in result for item in (sub if isinstance(sub, list) else [sub])]
                self.assertFalse(any("error" in item for item in flat), f"❌ Failed on: {sentence} → {result}")

                edge = next((item["content"] for item in flat if "from_node" in item.get("content", {})), None)
                self.assertIsNotNone(edge)
                self.assertEqual(edge["from_node"], subj)
                self.assertEqual(edge["to_node"], obj)
                self.assertEqual(edge["label"], "has")
                self.assertEqual(edge["cardinality"], card)

                added_nodes = [item["content"]["node"] for item in flat if "node" in item.get("content", {})]
                self.assertIn(obj, added_nodes)
                self.assertNotIn(subj, added_nodes)

    def test_invalid_sentences(self):
        sentences = [
            "Sunsets are beautiful.",
            "The sky looks blue.",
            "Happiness is important."
        ]
        for sentence in sentences:
            with self.subTest(sentence=sentence):
                result = self.parser.translate(sentence)
                flat = [item for sub in result for item in (sub if isinstance(sub, list) else [sub])]
                self.assertTrue(any("error" in item for item in flat))


class TestReverseHasDeclaration(unittest.TestCase):
    def setUp(self):
        self.parser = ReverseHasDeclaration()

    def test_part_of_relationships(self):
        cases = [
            ("There are multiple engines for each rocket.", "engine", "rocket", "*"),
            ("There is one propeller for each drone.", "propeller", "drone", "1"),
            ("Several wheels exist for every skateboard.", "wheel", "skateboard", "*"),
            ("At least one antenna is included for every satellite.", "antenna", "satellite", "+")
        ]
        for sentence, part, whole, card in cases:
            with self.subTest(sentence=sentence):
                result = self.parser.translate(sentence)
                flat = [item for sub in result for item in (sub if isinstance(sub, list) else [sub])]
                self.assertFalse(any("error" in item for item in flat), f"❌ Failed on: {sentence} → {result}")

                edge = next((item["content"] for item in flat if "from_node" in item.get("content", {})), None)
                self.assertIsNotNone(edge)
                # Expect normalized whole --has--> part
                self.assertEqual(edge["from_node"], whole)
                self.assertEqual(edge["to_node"], part)
                self.assertEqual(edge["label"], "has")
                self.assertEqual(edge["cardinality"], card)

                added_nodes = [item["content"]["node"] for item in flat if "node" in item.get("content", {})]
                self.assertIn(part, added_nodes)
                self.assertNotIn(whole, added_nodes)

    def test_invalid_sentences(self):
        invalids = [
            "Books are useful.",
            "Rockets fly into space.",
            "Happiness cannot be measured."
        ]
        for sentence in invalids:
            with self.subTest(sentence=sentence):
                result = self.parser.translate(sentence)
                flat = [item for sub in result for item in (sub if isinstance(sub, list) else [sub])]
                self.assertTrue(any("error" in item for item in flat))


class TestNodeDeclaration(unittest.TestCase):
    def setUp(self):
        self.parser = NodeDeclaration()

    def test_simple_nodes(self):
        cases = [
            ("Add a node called volcano.", "volcano"),
            ("Insert a node named satellite.", "satellite"),
            ("Create a node labeled mountain.", "mountain")
        ]
        for sentence, expected_id in cases:
            with self.subTest(sentence=sentence):
                result = self.parser.translate(sentence)
                flat = [item for sub in result for item in (sub if isinstance(sub, list) else [sub])]
                self.assertFalse(any("error" in item for item in flat), f"❌ Failed: {sentence} → {result}")

                node_entry = next((item["content"] for item in flat if "node" in item.get("content", {})), {})
                self.assertEqual(node_entry.get("node"), expected_id)

    def test_typed_nodes(self):
        cases = [
            ("Add a sensor named gyroscope.", "gyroscope", "sensor"),
            ("Create a device called thermometer.", "thermometer", "device"),
            ("Insert an object named camera.", "camera", "object")
        ]
        for sentence, node_id, expected_type in cases:
            with self.subTest(sentence=sentence):
                result = self.parser.translate(sentence)
                flat = [item for sub in result for item in (sub if isinstance(sub, list) else [sub])]
                self.assertFalse(any("error" in item for item in flat), f"❌ Failed: {sentence} → {result}")

                node_entry = next((item["content"] for item in flat if "node" in item.get("content", {})), {})
                self.assertEqual(node_entry.get("node"), node_id)
                self.assertIn(expected_type, node_entry.get("annotations", []))

    def test_invalid_node_sentences(self):
        invalids = [
            "The moon is bright.",
            "Stars twinkle at night.",
            "Music makes people happy."
        ]
        for sentence in invalids:
            with self.subTest(sentence=sentence):
                result = self.parser.translate(sentence)
                flat = [item for sub in result for item in (sub if isinstance(sub, list) else [sub])]
                self.assertTrue(any("error" in item for item in flat))


class TestDeleteDeclaration(unittest.TestCase):
    def setUp(self):
        self.parser = DeleteDeclaration()

    def test_valid_deletions(self):
        sentences = [
            "Delete the node named volcano.",
            "Erase the connection between engine and rocket.",
            "Delete the link from computer to monitor."
        ]
        for sentence in sentences:
            with self.subTest(sentence=sentence):
                result = self.parser.translate(sentence)
                self.assertTrue(any(item.get("update") == "delete" for item in result))

    def test_invalid_sentences(self):
        sentences = [
            "Please create a new node.",
            "Undo the last step.",
            "Describe the current graph."
        ]
        for sentence in sentences:
            with self.subTest(sentence=sentence):
                result = self.parser.translate(sentence)
                self.assertTrue(any("error" in item for item in result))


class TestUndoDeclaration(unittest.TestCase):
    def setUp(self):
        self.parser = UndoDeclaration()

    def test_valid_undo(self):
        sentences = [
            "Undo the last action.",
            "Go back one step.",
            "Revert the previous change.",
            "Undo."
        ]
        for sentence in sentences:
            with self.subTest(sentence=sentence):
                result = self.parser.translate(sentence)
                self.assertEqual(result[0]["update"], "undo")

    def test_invalid_undo(self):
        sentences = [
            "Add a node named balloon.",
            "Delete something.",
            "Please continue."
        ]
        for sentence in sentences:
            with self.subTest(sentence=sentence):
                result = self.parser.translate(sentence)
                self.assertTrue(any("error" in item for item in result))


if __name__ == "__main__":
    unittest.main()
