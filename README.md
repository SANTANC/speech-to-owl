# Speech to OWL Ontology

[![tests](https://github.com/GIO443/speech-to-owl/actions/workflows/tests.yml/badge.svg)](https://github.com/GIO443/speech-to-owl/actions/workflows/tests.yml)

Turn short spoken phrases into a standards-compliant OWL ontology (RDF/XML) you can use anywhere.

This app records audio in the browser, transcribes it, parses the text into structured updates (add class, add relation, delete, rename), and builds an OWL ontology using rdflib. You can view the resulting OWL in the UI and download it as `ontology.owl`.

## Quickstart

Prerequisites:
- Python 3.10+
- An OpenAI API key (for Whisper and the lightweight text parsers)

Setup:
1. Clone this repository.
2. Copy `.env.example` to `Project_Files/.env` and set `OPENAI_API_KEY`.
3. Install dependencies:
   - `pip install -r requirements.txt`

Run the app:
- `make run`
- Then open: http://localhost:5051

Run tests (text output):
- `make test`

Run tests with JUnit XML output:
- `make test-junit` (outputs to `Project_Files/test-reports/`)

If you do not have `make`:
- `python -m Project_Files.run_tests_junit` (JUnit XML)
- `python -m unittest discover -s Project_Files -p "test_*.py" -v` (text)
- `python -m Project_Files.main_app` (run app)

## What it does

- Frontend (Project_Files/templates/live.html):
  - Captures microphone audio.
  - Detects speech segments and sends audio chunks to the backend.
  - Displays the resulting OWL and provides a Download button.

- Backend (Project_Files/main_app.py):
  - `/` serves the UI.
  - `/stream` accepts audio, transcribes with Whisper, parses with small LLM prompts, and builds OWL via `OwlBuilder`.
  - `/owl` returns the current ontology serialized as RDF/XML.

- Transcript normalization (Project_Files/main_processing.py):
  - After transcription, we normalize the sentence to improve parsing:
    - Strip a leading wake/filler token if present: "command", "and", "so", "uh", "um", "well", "ok", "okay", "like" (case-insensitive; handles "command:"/"command,").
    - Trim whitespace and trailing punctuation.

- Parsing (Project_Files/*Declaration.py):
  - LLM-first to extract structured deltas (JSON). If LLM fails, NodeDeclaration has an expanded regex fallback that recognizes both imperative and declarative forms, e.g.:
    - add/create/make/define/insert [a|an|the] [class|node|entity|object|thing|concept|item] <name>
    - i have [a|an|the] [type] <name>
    - there is/there's [a|an] [type] <name>
    - [type] <name>

- OWL building (Project_Files/OwlBuilder.py):
  - Nodes map to `owl:Class`.
  - Relationships are modeled as `rdfs:subClassOf` `owl:Restriction` axioms with `owl:onProperty` and `owl:someValuesFrom`.
  - Canonical property is `:has`. `:part_of` is declared as `owl:inverseOf :has`.
  - Cardinality mapping:
    - `"n"` → `owl:cardinality n`
    - `"+"` → `owl:minCardinality 1`
    - `"*"` → `owl:minCardinality 0`
  - Reverse “part of” sentences are normalized to the canonical `has` direction.

## Architecture overview

- Audio transcription and normalization: `main_processing.py`
  - Transcribes audio with Faster-Whisper.
  - Applies `normalize_transcript()` to strip leading wake/filler tokens like "command", then routes text to parsers.
- Parsing: `*Declaration.py` classes use small LLM prompts to emit normalized deltas (JSON updates). Important: they do NOT change names (no auto-corrections).
  - NodeDeclaration includes expanded regex fallbacks for common command-style and declarative phrases.
- OWL construction: `OwlBuilder` consumes updates and maintains a graph, serializing to RDF/XML.

## Configuration

- Create `Project_Files/.env` with:
  - `OPENAI_API_KEY=your_key_here`

## Use it however you like

This project is intended for flexible use. You can:
- Use the provided frontend, or replace it with your own.
- Call the backend `/stream` with audio chunks, or bypass audio and feed text into the parsing pipeline.
- Extend or replace the parsers for your domain-specific phrasing.
- Customize OWL generation rules in `OwlBuilder` (namespaces, IRIs, property semantics).

The generated OWL is standard RDF/XML and can be used with any compatible tool.

## Troubleshooting

- `ModuleNotFoundError: rdflib`: run `pip install -r requirements.txt`.
- OpenAI API failures: ensure `.env` exists and contains a valid key.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

