# Usage Guide

This guide helps you run the application, speak sentences, and download the resulting OWL ontology.

## Start the application

1) Install dependencies:
- pip install -r requirements.txt

2) Configure your OpenAI key:
- Copy .env.example to Project_Files/.env
- Set OPENAI_API_KEY in that file

3) Run the server:
- make run
- Open http://localhost:5051 in your browser

## Speak and build the ontology

- Allow the microphone prompt in your browser.
- Tip: Use the wake word command to reliably start a phrase. The app strips command and fillers (and/so/uh/um/well/ok/okay/like) before parsing.
- Speak one short sentence, then pause; the app auto-detects silence and uploads a clip.
- The server transcribes, normalizes, parses, and updates the ontology. The OWL (RDF/XML) appears on the page and can be downloaded.

### Example sentences

- Add classes:
  - command add a node called volcano
  - command create a node named rocket
  - command I have a class car
- Add relationships:
  - command the car has four wheels
  - command a server has several drives
  - command there is one propeller for each drone (normalized to drone has propeller [1])
- Delete/rename:
  - command delete the node volcano
  - command rename rocket to launch vehicle

## Clarifications (near-duplicate names)

If a new class sounds like an existing one (e.g., band car vs car), the app may ask: “Did you mean car?” Use the on‑page Yes/No buttons to confirm before the change is applied.

## OWL modeling conventions

- Nodes → owl:Class
- Relations → rdfs:subClassOf owl:Restriction with owl:onProperty and owl:someValuesFrom
- Canonical property: :has; :part_of is owl:inverseOf :has
- Cardinalities:
  - "n" → owl:cardinality n
  - "+" → owl:minCardinality 1
  - "*" → owl:minCardinality 0
- “part of” phrasing is normalized to the canonical has direction

## Download OWL

- Click “Download OWL” to save ontology.owl
- Or call GET /owl to fetch the current RDF/XML

## Running tests locally

- make test
- Optional JUnit XML: make test-junit

## CI note

Automated CI tests are disabled by design to preserve LLM‑first behavior and avoid exposing secrets. A manual, no‑op workflow exists under .github/workflows/tests.yml (workflow_dispatch) if you need a placeholder run.

## Troubleshooting

- Mic prompt didn’t appear: check browser permissions and reload.
- No transcription: ensure your input device works; pause after speaking.
- OpenAI API issues: confirm OPENAI_API_KEY in Project_Files/.env and network access.
