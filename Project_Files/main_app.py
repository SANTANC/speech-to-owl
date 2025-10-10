import os
import json
import queue
import uuid
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from .main_processing import process_audio_file
from .OwlBuilder import OwlBuilder
import atexit

# Flask application serving the microphone UI and OWL endpoints
app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
OUTPUT_FOLDER = os.path.join(os.getcwd(), "Output")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

AGGREGATE_PATH = os.path.join(OUTPUT_FOLDER, "aggregate_output.json")
with open(AGGREGATE_PATH, "w") as f:
    json.dump([], f)

audio_queue = queue.Queue()
builder = OwlBuilder()

@app.route("/")
def index():
    return render_template("live.html")

@app.route("/stream", methods=["POST"])
def stream_audio_or_clarification():
    # JSON mode reserved for future: responding to clarification prompts if needed
    if request.is_json:
        data = request.get_json()
        if data.get("update") == "clarification":
            print("📩 Received clarification update.")
            result = builder.process(data)
            print("✅ Clarification processed:", result)
            return jsonify(result)
        return jsonify({"error": "Invalid JSON clarification input"}), 400

    if "file" not in request.files:
        print("❌ No audio file part found in request.")
        return jsonify({"error": "No audio file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        print("❌ Audio file has empty filename.")
        return jsonify({"error": "Empty filename"}), 400

    unique_filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    file.save(file_path)
    print(f"📥 Saved uploaded file to: {file_path}")

    try:
        print("🔍 ENTERED process_audio_input with file input")
        parsed_results = list(process_audio_file(file_path))
        print(f"🧠 Parsed results: {parsed_results}")

        for result in parsed_results:
            if result.get("type") == "parsed":
                updates = result["output"]
                if isinstance(updates, dict):
                    updates = [updates]
                print(f"📎 Processing updates into OWL: {updates}")
                result_obj = builder.process(updates)
                print("📤 Result from OwlBuilder:", result_obj)
                return jsonify(result_obj)


        print("⚠️ No valid parsed updates found.")
        return jsonify({"message": "No valid parsed updates."})

    except Exception:
        import traceback
        traceback.print_exc()
        raise



@app.route("/owl")
def get_owl():
    try:
        owl_xml = builder.serialize()
        return jsonify({
            "content_type": "application/rdf+xml",
            "owl": owl_xml
        })
    except Exception as e:
        return jsonify({"error": f"Failed to serialize OWL: {str(e)}"}), 500

atexit.register(lambda: [os.remove(os.path.join(UPLOAD_FOLDER, f)) for f in os.listdir(UPLOAD_FOLDER)])

if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        print("📦 Loaded ApplicationBuilder with ontology and dataflow graphs.")
    app.run(debug=True, threaded=True, host="0.0.0.0", port=5051
            )
