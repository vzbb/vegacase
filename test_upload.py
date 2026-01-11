import os
import time
from dotenv import load_dotenv
from google import genai

load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")
print(f"API Key present: {bool(API_KEY)}", flush=True)

client = genai.Client(api_key=API_KEY)

print("Listing models...", flush=True)
try:
    # Iterate to force the request
    for m in client.models.list():
        print(f"Found model: {m.name}", flush=True)
        break
    print("List models successful.", flush=True)
except Exception as e:
    print(f"List models failed: {e}", flush=True)
    exit(1)

# Create a dummy file to upload
with open("test.txt", "w") as f:
    f.write("This is a test file for Gemini API upload.")

print("Uploading test.txt...", flush=True)
try:
    file_obj = client.files.upload(file="test.txt")
    print(f"Upload initiated: {file_obj.name}", flush=True)
    
    while file_obj.state.name == "PROCESSING":
        print("Processing...", flush=True)
        time.sleep(1)
        file_obj = client.files.get(name=file_obj.name)
        
    print(f"Final state: {file_obj.state.name}", flush=True)
    
    # Clean up
    client.files.delete(name=file_obj.name)
    print("Deleted test file.", flush=True)
    
except Exception as e:
    print(f"Upload failed: {e}", flush=True)

if os.path.exists("test.txt"):
    os.remove("test.txt")
