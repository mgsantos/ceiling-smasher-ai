from google import genai
import os
import warnings

warnings.filterwarnings("ignore")

api_key = os.environ.get("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)

try:
    print("Listing Available Models (google-genai SDK 1.47+):")
    # In the new SDK, client.models.list() returns an iterator of models
    for m in client.models.list():
        print(f"- {m.name} (ID: {m.name.split('/')[-1]})")
except Exception as e:
    print(f"Error: {e}")
