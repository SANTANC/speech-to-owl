import os
import json
import traceback
import torch
from faster_whisper import WhisperModel
from .ParserDecider import ParserDecider

# --- Initialize components ---
parser_decider = ParserDecider(model="gpt-3.5-turbo")

# Load Whisper model ONCE
WHISPER_MODEL_SIZE = "base"  # or "tiny", "small"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
model = WhisperModel(WHISPER_MODEL_SIZE, device=DEVICE, compute_type="float16" if DEVICE == "cuda" else "int8")

def transcribe_audio(file_path: str) -> str:
    try:
        print(f"🧠 Transcribing with Faster-Whisper on {DEVICE}")
        segments, _ = model.transcribe(file_path, beam_size=1)  # fast decode
        full_text = " ".join([segment.text.strip() for segment in segments])
        return full_text
    except Exception as e:
        print(f"❌ Whisper transcription failed: {e}")
        return ""

def normalize_transcript(s: str) -> str:
    """Strip a leading wake/filler token to make parsing robust.
    Handles: command[,|: ], and, so, uh, um, well, ok, okay, like.
    """
    import re
    s = s.strip()
    # Remove leading punctuation-separated wake word
    s = re.sub(r"^(command)\s*[:,]?\s+", "", s, flags=re.IGNORECASE)
    # Remove generic filler words at the very start
    s = re.sub(r"^(and|so|uh|um|well|ok|okay|like)\s+", "", s, flags=re.IGNORECASE)
    return s.strip()

def process_audio_file(input_data: str, is_path=True):
    print(f"🔍 ENTERED process_audio_input with {'file' if is_path else 'text'} input")

    if is_path:
        OUTPUT_DIR = os.path.join(os.getcwd(), "Output")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        AGGREGATE_PATH = os.path.join(OUTPUT_DIR, "aggregate_output.json")

    parsed_count = 0
    unparsed_count = 0
    final_entries = []

    try:
        if is_path:
            if os.path.getsize(input_data) < 1000:
                print("🔝 File too small, treating as silence.")
                return []

            sentence = transcribe_audio(input_data)
        else:
            sentence = input_data.strip()

        # Normalize transcript: remove wake/filler words like 'command', 'and', 'so', etc.
        sentence = sentence.lower().strip()
        sentence = normalize_transcript(sentence)
        if not sentence:
            print("⚠️ No transcription result.")
            return []

        print(f"🎙️ Sentence to parse: {sentence}")
        parsed_data = parser_decider.parse(sentence, return_with_parser=True)
        label = parsed_data.get("label", "None")
        parsed_output = parsed_data.get("result")

        print(f"🧠 Parser: {label}")
        print(f"📤 Parser output: {parsed_output}")

        is_valid_list = isinstance(parsed_output, list) and parsed_output and "error" not in parsed_output[0]
        is_valid_dict = isinstance(parsed_output, dict) and "error" not in parsed_output

        if is_valid_list or is_valid_dict:
            if is_valid_list:
                for item in parsed_output:
                    final_entries.append(item)
            else:
                final_entries.append(parsed_output)

            parsed_count += 1
            yield {
                "type": "parsed",
                "parser": label,
                "input": sentence,
                "output": parsed_output
            }
        else:
            print(f"⚠️ Failed to parse: {sentence}")
            final_entries.append({
                "type": "unparsed",
                "input": sentence
            })
            unparsed_count += 1
            yield {
                "type": "unparsed",
                "input": sentence
            }

    except Exception as e:
        print(f"❌ Exception in process_audio_input: {e}")
        traceback.print_exc()

    finally:
        if is_path:
            try:
                if os.path.exists(AGGREGATE_PATH):
                    with open(AGGREGATE_PATH, "r") as f:
                        existing_data = json.load(f)
                else:
                    existing_data = []
            except Exception as e:
                print(f"⚠️ Failed to load existing aggregate file: {e}")
                existing_data = []

            with open(AGGREGATE_PATH, "w") as f:
                json.dump(existing_data + final_entries, f, indent=2)

            print(f"✅ FINISHED process_audio_input for: {input_data}")
            print(f"📊 Summary — Parsed: {parsed_count}, Unparsed: {unparsed_count}")
