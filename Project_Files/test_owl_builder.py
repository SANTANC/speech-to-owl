"""OWL builder unit tests (rdflib)

These tests verify that OwlBuilder converts normalized deltas into a valid
OWL ontology (RDF/XML). They cover property declarations, class creation,
restrictions with cardinalities, normalization of part_of to has, and
rename/delete behavior, as well as round-trip serialization sanity.
"""
import re
import unittest
from rdflib import Graph, Namespace, RDF, RDFS, OWL
from Project_Files_path_fix import builder_serialize_from_updates

BASE = 'http://example.org/onto#'
NS = Namespace(BASE)


class TestOwlBuilder(unittest.TestCase):
    def as_graph(self, owl_xml: str) -> Graph:
        g = Graph()
        g.parse(data=owl_xml, format='xml')
        return g

    # ------------------------------------------------------------------
    # Core declarations
    # ------------------------------------------------------------------
    def test_namespace_and_inverse_properties(self):
        owl_xml = builder_serialize_from_updates([])
        g = self.as_graph(owl_xml)
        # :has and :part_of exist
        self.assertIn((NS.has, RDF.type, OWL.ObjectProperty), g)
        self.assertIn((NS.part_of, RDF.type, OWL.ObjectProperty), g)
        # inverseOf declared both ways
        self.assertIn((NS.part_of, OWL.inverseOf, NS.has), g)
        self.assertIn((NS.has, OWL.inverseOf, NS.part_of), g)

    def test_add_node_creates_class(self):
        owl_xml = builder_serialize_from_updates([
            {"update": "add", "content": {"node": "Volcano"}}
        ])
        g = self.as_graph(owl_xml)
        self.assertIn((NS.Volcano, RDF.type, OWL.Class), g)

    def test_multiple_classes_and_idempotent_add(self):
        owl_xml = builder_serialize_from_updates([
            {"update": "add", "content": {"node": "Car"}},
            {"update": "add", "content": {"node": "Car"}},
            {"update": "add", "content": {"node": "Wheel"}},
        ])
        g = self.as_graph(owl_xml)
        # Still only expects presence; rdflib graph handles duplicate triple elimination
        self.assertIn((NS.Car, RDF.type, OWL.Class), g)
        self.assertIn((NS.Wheel, RDF.type, OWL.Class), g)

    def test_safe_name_normalization(self):
        owl_xml = builder_serialize_from_updates([
            {"update": "add", "content": {"node": "Paris, France"}},
            {"update": "add", "content": {"from_node": "Car Model 3", "to_node": "Front Wheel", "label": "has", "cardinality": "1"}},
        ])
        g = self.as_graph(owl_xml)
        # Commas and spaces should become underscores
        self.assertIn((NS.Paris_France, RDF.type, OWL.Class), g)
        # Property restriction exists with normalized class names
        # We verify the existence indirectly by checking that both classes exist
        self.assertIn((NS.Car_Model_3, RDF.type, OWL.Class), g)
        self.assertIn((NS.Front_Wheel, RDF.type, OWL.Class), g)

    # ------------------------------------------------------------------
    # Restrictions and cardinality
    # ------------------------------------------------------------------
    def test_multiple_numeric_cardinalities(self):
        for n in ["1", "2", "10"]:
            with self.subTest(card=n):
                owl_xml = builder_serialize_from_updates([
                    {"update": "add", "content": {"from_node": "Device", "to_node": f"Port{n}", "label": "has", "cardinality": n}}
                ])
                # Confirm cardinality n restriction exists in raw XML
                self.assertRegex(owl_xml, rf"owl:cardinality[^>]*>{n}<")

    def test_min_cardinality_plus_and_star(self):
        owl_plus = builder_serialize_from_updates([
            {"update": "add", "content": {"from_node": "Robot", "to_node": "Sensor", "label": "has", "cardinality": "+"}}
        ])
        self.assertRegex(owl_plus, r"owl:minCardinality[^>]*>1<")

        owl_star = builder_serialize_from_updates([
            {"update": "add", "content": {"from_node": "Server", "to_node": "Drive", "label": "has", "cardinality": "*"}}
        ])
        self.assertRegex(owl_star, r"owl:minCardinality[^>]*>0<")

    def test_multiple_restrictions_same_class(self):
        owl_xml = builder_serialize_from_updates([
            {"update": "add", "content": {"node": "Car"}},
            {"update": "add", "content": {"from_node": "Car", "to_node": "Wheel", "label": "has", "cardinality": "+"}},
            {"update": "add", "content": {"from_node": "Car", "to_node": "Door", "label": "has", "cardinality": "4"}},
        ])
        g = self.as_graph(owl_xml)
        # Both Wheel and Door classes exist, and Car is a Class
        self.assertIn((NS.Car, RDF.type, OWL.Class), g)
        self.assertIn((NS.Wheel, RDF.type, OWL.Class), g)
        self.assertIn((NS.Door, RDF.type, OWL.Class), g)
        # There should be at least two subclass axioms off Car
        subs = list(g.triples((NS.Car, RDFS.subClassOf, None)))
        self.assertGreaterEqual(len(subs), 2)

    def test_multiple_properties_and_restrictions(self):
        owl_xml = builder_serialize_from_updates([
            {"update": "add", "content": {"from_node": "Printer", "to_node": "Hub", "label": "connected", "cardinality": "+"}},
            {"update": "add", "content": {"from_node": "Printer", "to_node": "Printer", "label": "closeby", "cardinality": "1"}},
        ])
        g = self.as_graph(owl_xml)
        # New properties should exist as ObjectProperty with safe names
        self.assertIn((NS.connected, RDF.type, OWL.ObjectProperty), g)
        self.assertIn((NS.closeby, RDF.type, OWL.ObjectProperty), g)

    # ------------------------------------------------------------------
    # Normalization, rename, delete
    # ------------------------------------------------------------------
    def test_reverse_part_of_normalization(self):
        owl_xml = builder_serialize_from_updates([
            {"update": "add", "content": {"from_node": "engine", "to_node": "rocket", "label": "part of", "cardinality": "*"}}
        ])
        g = self.as_graph(owl_xml)
        # Expect a restriction on Rocket with property :has and someValuesFrom :engine
        # Check at least the property is :has and both classes exist
        self.assertIn((NS.engine, RDF.type, OWL.Class), g)
        self.assertIn((NS.rocket, RDF.type, OWL.Class), g)
        # Ensure onProperty is :has exists somewhere
        self.assertTrue(any(p == OWL.onProperty and o == NS.has for s,p,o in g), "Expected onProperty :has in restrictions")

    def test_rename_updates_references(self):
        owl_xml = builder_serialize_from_updates([
            {"update": "add", "content": {"from_node": "A", "to_node": "B", "label": "has", "cardinality": "+"}},
            {"update": "rename", "content": {"from": "A", "to": "C"}},
        ])
        g = self.as_graph(owl_xml)
        # old class removed, new class exists
        self.assertNotIn((NS.A, RDF.type, OWL.Class), g)
        self.assertIn((NS.C, RDF.type, OWL.Class), g)
        # B still present
        self.assertIn((NS.B, RDF.type, OWL.Class), g)

    def test_delete_removes_class_only(self):
        owl_xml = builder_serialize_from_updates([
            {"update": "add", "content": {"node": "Tmp"}},
            {"update": "delete", "content": {"id": "Tmp"}},
            {"update": "add", "content": {"node": "Other"}},
        ])
        g = self.as_graph(owl_xml)
        self.assertNotIn((NS.Tmp, RDF.type, OWL.Class), g)
        self.assertIn((NS.Other, RDF.type, OWL.Class), g)

    def test_round_trip_serialize_parse(self):
        owl_xml = builder_serialize_from_updates([
            {"update": "add", "content": {"node": "R1"}},
            {"update": "add", "content": {"from_node": "R1", "to_node": "R2", "label": "has", "cardinality": "2"}},
        ])
        g1 = self.as_graph(owl_xml)
        # serialize again and re-parse; should remain valid
        xml2 = g1.serialize(format='xml')
        g2 = Graph().parse(data=xml2, format='xml')
        # Basic sanity: same number of triples or more in g2 (bindings may add triples)
        self.assertGreaterEqual(len(g2), len(g1))


if __name__ == '__main__':
    unittest.main()
