# Usage Guide

This guide helps you run the application, speak sentences, and download the resulting OWL ontology.

## Start the application

1. Install dependencies: `pip install -r requirements.txt`
2. Copy `.env.example` to `Project_Files/.env` and set `OPENAI_API_KEY`.
3. Run the server: `make run` (or `python -m Project_Files.main_app`).
4. Open http://localhost:5051 in your browser.

## Speak and build ontology

- The page will automatically start the microphone (grant permission when asked).
- Tip: You can say "command" at the start as a wake word. It and other fillers (and/so/uh/um/well/ok/okay/like) are removed before parsing.
- Speak a short sentence, pause; the app detects silence and sends the audio chunk.
- The server transcribes, normalizes the text, parses, and updates the ontology.
- The OWL (RDF/XML) appears in the page and can be downloaded.

### Example sentences

- Add classes:
  - "In the ontology graph, add a node called Volcano."
  - "Create a node named Rocket."
  - "command I have a class car"
  - "there is an entity volcano"
  - "object control panel"
  - "define concept rocket engine"
- Add relationships:
  - "The car has four wheels."
  - "A server has several drives."
  - "There is one propeller for each drone." (normalized to `Drone has Propeller`)
- Delete/rename:
  - "Delete the node 'Volcano'."
  - "Rename Rocket to Launch Vehicle."

## OWL modeling conventions

- Each node becomes an `owl:Class`.
- Relations are class axioms: `rdfs:subClassOf` \[ `owl:Restriction` ; `owl:onProperty` :has ; `owl:someValuesFrom` :Object ; cardinality facet \].
- Canonical property: `:has`. `:part_of` is declared as `owl:inverseOf :has`. Reverse “part of” sentences are normalized to `has`.
- Cardinalities:
  - `"n"` → `owl:cardinality n`
  - `"+"` → `owl:minCardinality 1`
  - `"*"` → `owl:minCardinality 0`

## Download OWL

- Click the "Download OWL" button on the page.
- Or call `GET /owl` to retrieve the RDF/XML string.

## Notes

- For best results, speak simple, single-sentence commands.
- The parser does not auto-correct names; "pinter" will create a class `:pinter`.
