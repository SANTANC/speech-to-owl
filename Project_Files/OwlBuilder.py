from rdflib import Graph, Namespace, RDF, RDFS, OWL, BNode, Literal, URIRef
from rdflib.namespace import XSD
import difflib


class OwlBuilder:
    """
    Builds an OWL ontology using RDF/XML based on normalized update deltas.

    Conventions:
    - Nodes map to owl:Class
    - Relationships are encoded as rdfs:subClassOf owl:Restriction with owl:onProperty
    - Canonical property is :has; :part_of is declared as its inverse
    - Cardinality mapping:
        "1" or numeric n -> owl:cardinality n
        "+" -> owl:minCardinality 1
        "*" -> owl:minCardinality 0

    Typical usage:
        builder = OwlBuilder()
        result = builder.process([
            {"update": "add", "content": {"node": "Car"}},
            {"update": "add", "content": {"from_node": "Car", "to_node": "Wheel", "label": "has", "cardinality": "4"}},
        ])
        owl_xml = result["owl"]
    """

    def __init__(self, base_iri: str = "http://example.org/onto#"):
        self.base_iri = base_iri
        self.g = Graph()
        self.NS = Namespace(base_iri)
        self.g.bind("", self.NS)
        self.g.bind("owl", OWL)
        self.g.bind("rdfs", RDFS)
        self.g.bind("rdf", RDF)
        self.g.bind("xsd", XSD)

        # State for clarification flows
        self._pending = None  # type: dict | None
        self._queue = []      # list of updates awaiting after clarification
        self._cutoff = 0.85   # fuzzy match cutoff

        # Define core object properties: has and part_of (inverse)
        # Consumers should always use 'has' in updates; 'part of' will be normalized.
        self._ensure_object_property("has")
        self._ensure_object_property("part_of")
        # Declare the inverse relation explicitly in the ontology
        self.g.add((self.NS.part_of, OWL.inverseOf, self.NS.has))
        self.g.add((self.NS.has, OWL.inverseOf, self.NS.part_of))

    def serialize(self) -> str:
        return self.g.serialize(format="xml").decode("utf-8") if isinstance(self.g.serialize(format="xml"), bytes) else self.g.serialize(format="xml")

    # Public API ---------------------------------------------------------------
    def process(self, updates):
        # Normalize to a list for unified processing
        if isinstance(updates, dict):
            updates = [updates]

        # Clarification handling
        if len(updates) == 1 and updates[0].get("update") == "clarification":
            return self._process_clarification(updates[0].get("content", {}).get("response", ""))

        messages = []
        for i, upd in enumerate(updates):
            if upd.get("update") == "add":
                content = upd.get("content", {})
                if "node" in content:
                    name = content["node"].strip()
                    suggestion = self._find_similar_class(name)
                    if suggestion:
                        # store pending and queue the rest
                        self._pending = {"type": "add_node", "name": name, "suggestion": suggestion}
                        self._queue = updates[i+1:]
                        return {
                            "kind": "clarification",
                            "message": f"A class similar to '{name}' exists: '{suggestion}'. Did you mean '{suggestion}'? Yes or No.",
                        }
                    self.add_class(name)
                    messages.append(f"Class {name} added")
                elif {"from_node", "to_node"}.issubset(content.keys()):
                    subj = content["from_node"].strip()
                    obj = content["to_node"].strip()
                    label = (content.get("label") or "has").strip()
                    card = (content.get("cardinality") or "*").strip()
                    # Normalize: if label is 'part of' or variants, flip direction to has
                    if label.lower().replace(" ", "") in {"partof", "part_of", "part-of"}:
                        label = "has"
                        subj, obj = obj, subj
                    # For restrictions, prompt only for classes not yet known
                    to_check = []
                    if not self._class_exists(subj):
                        to_check.append(("subject", subj))
                    if not self._class_exists(obj):
                        to_check.append(("object", obj))
                    for role, candidate in to_check:
                        suggestion = self._find_similar_class(candidate)
                        if suggestion:
                            self._pending = {
                                "type": "add_restriction",
                                "subj": subj,
                                "obj": obj,
                                "label": label,
                                "card": card,
                                "role": role,
                                "name": candidate,
                                "suggestion": suggestion,
                            }
                            self._queue = updates[i+1:]
                            return {
                                "kind": "clarification",
                                "message": f"A class similar to '{candidate}' exists: '{suggestion}'. Did you mean '{suggestion}'? Yes or No.",
                            }
                    self.add_restriction(subj, label, obj, card)
                    messages.append(f"Restriction added: {subj} {label} {obj} [{card}]")
                else:
                    messages.append("Unsupported add content")

            elif upd.get("update") == "delete":
                content = upd.get("content", {})
                if "id" in content:
                    name = content["id"].strip()
                    self.delete_class(name)
                    messages.append(f"Class {name} deleted")
                else:
                    messages.append("Unsupported delete content")

            elif upd.get("update") == "rename":
                content = upd.get("content", {})
                old = content.get("from")
                new = content.get("to")
                if isinstance(old, str) and isinstance(new, str):
                    self.rename_class(old.strip(), new.strip())
                    messages.append(f"Class {old} renamed to {new}")
                else:
                    messages.append("Invalid rename content")

        return {
            "kind": "success",
            "message": "; ".join(messages) if messages else "No changes",
            "content_type": "application/rdf+xml",
            "owl": self.serialize(),
        }

    # Primitives ---------------------------------------------------------------
    def add_class(self, name: str):
        iri = self._class_iri(name)
        self.g.add((iri, RDF.type, OWL.Class))
        return iri

    def delete_class(self, name: str):
        iri = self._class_iri(name)
        # Remove all triples where this IRI appears as subject or object.
        # This is a best-effort delete (no reasoning), suitable for a design session.
        triples = list(self.g.triples((iri, None, None))) + list(self.g.triples((None, None, iri)))
        for t in triples:
            self.g.remove(t)

    def rename_class(self, old: str, new: str):
        old_iri = self._class_iri(old)
        new_iri = self._class_iri(new)
        # copy all triples from old to new, replacing occurrences
        for s, p, o in list(self.g.triples((None, None, None))):
            s2 = new_iri if s == old_iri else s
            o2 = new_iri if o == old_iri else o
            if (s2, p, o2) != (s, p, o):
                self.g.add((s2, p, o2))
        # ensure class type
        self.g.add((new_iri, RDF.type, OWL.Class))
        # remove old
        self.delete_class(old)

    def add_restriction(self, subject_class: str, label: str, object_class: str, cardinality: str):
        subj_iri = self.add_class(subject_class)
        obj_iri = self.add_class(object_class)
        prop_iri = self._ensure_object_property(self._safe_name(label))

        # Build restriction blank node
        r = BNode()
        self.g.add((subj_iri, RDFS.subClassOf, r))
        self.g.add((r, RDF.type, OWL.Restriction))
        self.g.add((r, OWL.onProperty, prop_iri))
        self.g.add((r, OWL.someValuesFrom, obj_iri))

        # Cardinality facet
        if cardinality.isdigit():
            self.g.add((r, OWL.cardinality, Literal(int(cardinality), datatype=XSD.nonNegativeInteger)))
        else:
            c = cardinality.strip()
            if c == "+":
                self.g.add((r, OWL.minCardinality, Literal(1, datatype=XSD.nonNegativeInteger)))
            elif c == "*":
                self.g.add((r, OWL.minCardinality, Literal(0, datatype=XSD.nonNegativeInteger)))
            # else: ignore unknown tokens

    def _process_clarification(self, response: str):
        if not self._pending:
            return {
                "kind": "error",
                "message": "No pending clarification to process.",
                "content_type": "application/rdf+xml",
                "owl": self.serialize(),
            }
        affirmative = response.strip().lower() in {"yes", "y"}
        pend = self._pending
        self._pending = None

        messages = []
        # Resolve with suggested or original name(s)
        if pend["type"] == "add_node":
            final_name = pend["suggestion"] if affirmative else pend["name"]
            self.add_class(final_name)
            messages.append(f"Class {final_name} added")
        elif pend["type"] == "add_restriction":
            subj = pend["subj"]
            obj = pend["obj"]
            if affirmative:
                if pend["role"] == "subject":
                    subj = pend["suggestion"]
                else:
                    obj = pend["suggestion"]
            # Ensure classes
            self.add_class(subj)
            self.add_class(obj)
            self.add_restriction(subj, pend["label"], obj, pend["card"])
            messages.append(f"Restriction added: {subj} {pend['label']} {obj} [{pend['card']}]")

        # Continue queued updates, if any
        if self._queue:
            next_updates = self._queue
            self._queue = []
            cont = self.process(next_updates)
            if cont.get("kind") == "batch":
                # unlikely but support nested batches
                responses = cont["responses"]
            else:
                responses = [cont]
            return {
                "kind": "batch",
                "responses": [
                    {
                        "kind": "success",
                        "message": "; ".join(messages) if messages else "No changes",
                        "content_type": "application/rdf+xml",
                        "owl": self.serialize(),
                    }
                ] + responses,
            }

        return {
            "kind": "success",
            "message": "; ".join(messages) if messages else "No changes",
            "content_type": "application/rdf+xml",
            "owl": self.serialize(),
        }

    # Helpers ------------------------------------------------------------------
    def _class_iri(self, name: str) -> URIRef:
        return self.NS[self._safe_name(name)]

    def _ensure_object_property(self, name: str) -> URIRef:
        iri = self.NS[self._safe_name(name)]
        if (iri, RDF.type, OWL.ObjectProperty) not in self.g:
            self.g.add((iri, RDF.type, OWL.ObjectProperty))
        return iri

    def _class_exists(self, name: str) -> bool:
        iri = self._class_iri(name)
        return (iri, RDF.type, OWL.Class) in self.g

    def _find_similar_class(self, name: str) -> str | None:
        # Gather known class labels from current graph (local names)
        known = [str(s).split('#')[-1] for s, p, o in self.g.triples((None, RDF.type, OWL.Class))]
        target = self._safe_name(name)
        candidates = [k for k in known if k != target]
        # 1) Fuzzy match first
        matches = difflib.get_close_matches(target, candidates, n=1, cutoff=self._cutoff)
        if matches:
            return matches[0]
        # 2) Token/suffix heuristic: catch prefix noise like "band_car" vs "car"
        tokens = target.split('_')
        if tokens:
            last = tokens[-1]
            if last in candidates:
                return last
            if len(tokens) >= 2:
                suffix = '_'.join(tokens[1:])
                if suffix in candidates:
                    return suffix
        return None

    @staticmethod
    def _safe_name(name: str) -> str:
        # Create a simple IRI-friendly local name: strip spaces, non-word -> '_'
        import re
        s = name.strip()
        # Replace separators with underscores
        s = re.sub(r"[^A-Za-z0-9]+", "_", s)
        # Avoid leading digits
        if s and s[0].isdigit():
            s = "_" + s
        return s or "Entity"
