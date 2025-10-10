# Development Guide

This document describes the repo structure, the core components, and how to extend or test the project.

## Project structure (key files)

- Project_Files/
  - main_app.py — Flask app with `/`, `/stream`, `/owl`
  - OwlBuilder.py — Builds an OWL ontology (RDF/XML) from normalized updates
  - Translator.py — OpenAI Whisper transcription
  - *Declaration.py — Parsers that turn text into normalized deltas
  - test_phrase_parser.py — Parser tests
  - test_owl_builder.py — OWL builder tests (rdflib-based)
  - run_tests_junit.py — JUnit XML test runner (xmlrunner)
- README.md — Overview + quickstart
- requirements.txt — Python dependencies
- docs/ — Usage and development docs

## Core flow

1. Browser records audio and POSTs to `/stream`.
2. main_app.py saves the file, calls process_audio_file (transcribe + normalize + parse).
3. main_processing.normalize_transcript strips leading wake/filler words like "command", "and", "so", "uh/um", "well", "ok/okay", "like".
4. Declarations produce normalized updates (deltas).
5. OwlBuilder processes deltas and updates the ontology graph.
6. UI displays updated RDF/XML; `/owl` returns the current ontology.

## Deltas (update format)

- Add class:
  - `{ "update": "add", "content": { "node": "Car", "annotations": [] } }`
- Add restriction (has relation):
  - `{ "update": "add", "content": { "from_node": "Car", "to_node": "Wheel", "label": "has", "cardinality": "4" } }`
- Delete class:
  - `{ "update": "delete", "content": { "id": "Car" } }`
- Rename class:
  - `{ "update": "rename", "content": { "from": "Car", "to": "Vehicle" } }`

Notes:
- Reverse “part of” is normalized to `has` with direction flipped (whole has part).
- Unknown labels are created as new `owl:ObjectProperty` IRIs.

## Coding guidelines

- Keep prompts in Declaration classes strict and JSON-only to minimize parsing errors.
- Avoid clever auto-corrections of names; pass raw strings to the OWL layer.
- Add small, clear docstrings per function.

## Running

- App:
  - `make run` or `python -m Project_Files.main_app`
- Tests (text):
  - `make test` or `python -m unittest discover -s Project_Files -p "test_*.py" -v`
- Tests (JUnit XML):
  - `make test-junit` or `python -m Project_Files.run_tests_junit`

## Extending

- New parser: create `NewDeclaration.py` with a Statement subclass.
- Return normalized deltas as shown above.
- OwlBuilder will consume them and update the ontology.
- NodeDeclaration regex fallback recognizes forms like:
  - add/create/make/define/insert [a|an|the] [class|node|entity|object|thing|concept|item] <name>
  - i have [a|an|the] [type] <name>
  - there is/there's [a|an] [type] <name>
  - [type] <name>

## CI (optional)

You can add a GitHub Actions workflow:

```
name: tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python -m Project_Files.run_tests_junit
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: junit-xml
          path: "Project_Files/test-reports/*.xml"
```
