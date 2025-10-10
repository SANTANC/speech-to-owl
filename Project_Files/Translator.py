from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

class Translator:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)

    def translate(self, audio_file_path):
        with open(audio_file_path, "rb") as file:
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=file
            )
        return transcript.text
