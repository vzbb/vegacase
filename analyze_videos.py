import os
import time
import glob
import json
import logging
import socket
import argparse
import sys
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Force IPv4 to prevent connection stalls
old_getaddrinfo = socket.getaddrinfo
def new_getaddrinfo(*args, **kwargs):
    responses = old_getaddrinfo(*args, **kwargs)
    return [response for response in responses if response[0] == socket.AF_INET]
socket.getaddrinfo = new_getaddrinfo

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("video_analysis.log"),
        logging.StreamHandler()
    ]
)

# Configuration
API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_ID = "gemini-3-pro-preview" 
VIDEO_DIR = "video"
CONTEXT_DIR = "context"
UPLOAD_CACHE_FILE = "upload_cache.json"

if not API_KEY:
    logging.error("GEMINI_API_KEY environment variable not set.")
    exit(1)

def load_json_file(filepath, default):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logging.warning(f"Could not decode {filepath}, using default.")
    return default

def save_json_file(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

class UploadManager:
    def __init__(self, client):
        self.client = client
        self.upload_cache = load_json_file(UPLOAD_CACHE_FILE, {})

    def get_remote_file(self, file_name):
        try:
            return self.client.files.get(name=file_name)
        except Exception:
            return None

    def upload_file_cached(self, file_path, mime_type=None):
        file_stats = os.stat(file_path)
        file_key = f"{file_path}_{file_stats.st_size}_{file_stats.st_mtime}"
        
        cached_info = self.upload_cache.get(file_path)
        
        if cached_info and cached_info.get("key") == file_key:
            name = cached_info.get("name")
            logging.info(f"Checking cached file {file_path} ({name})...")
            remote_file = self.get_remote_file(name)
            if remote_file and remote_file.state.name == "ACTIVE":
                logging.info(f"File {file_path} already active on server.")
                return remote_file
            else:
                logging.info(f"Cached file {name} not found or not active. Re-uploading.")
        
        logging.info(f"Uploading {file_path}...")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Upload the file
                file_obj = self.client.files.upload(file=file_path, config={'mime_type': mime_type} if mime_type else None)
                logging.info(f"Uploaded {file_path} as {file_obj.name}")
                
                # Wait for processing
                start_time = time.time()
                while file_obj.state.name == "PROCESSING":
                    if time.time() - start_time > 600:
                        logging.error(f"Timeout waiting for {file_path} to process.")
                        return None
                    time.sleep(5)
                    file_obj = self.client.files.get(name=file_obj.name)
                    
                if file_obj.state.name != "ACTIVE":
                    logging.error(f"File {file_path} failed to process: {file_obj.state.name}")
                    return None
                    
                # Update cache
                self.upload_cache[file_path] = {
                    "name": file_obj.name,
                    "uri": file_obj.uri,
                    "key": file_key
                }
                save_json_file(UPLOAD_CACHE_FILE, self.upload_cache)
                return file_obj

            except Exception as e:
                logging.error(f"Upload attempt {attempt + 1}/{max_retries} failed for {file_path}: {e}")
                time.sleep(5 * (attempt + 1))
                
        return None

    def list_files(self):
        print("\n--- Local Video Files ---")
        video_files = sorted(glob.glob(os.path.join(VIDEO_DIR, "**/*.mp4"), recursive=True))
        for i, vf in enumerate(video_files):
            cached = self.upload_cache.get(vf)
            status = " [NOT UPLOADED]"
            if cached:
                status = f" [UPLOADED: {cached['name']}]"
            print(f"{i+1}. {vf}{status}")
        return video_files

    def interactive_menu(self):
        while True:
            video_files = self.list_files()
            print("\nOptions:")
            print("1. Upload all missing files")
            print("2. Force re-upload a specific file")
            print("3. Exit Upload Manager")
            
            choice = input("Enter choice: ")
            
            if choice == "1":
                for vf in video_files:
                    self.upload_file_cached(vf, mime_type="video/mp4")
            elif choice == "2":
                try:
                    idx = int(input("Enter file number to re-upload: ")) - 1
                    if 0 <= idx < len(video_files):
                        vf = video_files[idx]
                        if vf in self.upload_cache:
                            del self.upload_cache[vf] # Clear cache to force upload
                        self.upload_file_cached(vf, mime_type="video/mp4")
                    else:
                        print("Invalid index.")
                except ValueError:
                    print("Invalid input.")
            elif choice == "3":
                break

class RunManager:
    def __init__(self, run_id=None):
        if run_id:
            self.run_id = run_id
        else:
            self.run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
        self.results_dir = os.path.join("results", self.run_id)
        os.makedirs(self.results_dir, exist_ok=True)
        logging.info(f"Run Manager Initialized. Run ID: {self.run_id}. Results Dir: {self.results_dir}")

    def get_run_id(self):
        return self.run_id

    def get_processed_files(self):
        processed = set()
        for f in glob.glob(os.path.join(self.results_dir, "*.json")):
            try:
                data = load_json_file(f, {})
                if "filename" in data:
                    processed.add(data["filename"])
            except:
                pass
        return processed

    def get_previous_insights(self):
        insights = []
        for f in glob.glob(os.path.join(self.results_dir, "*.json")):
            try:
                data = load_json_file(f, {})
                if "insights" in data and isinstance(data["insights"], list):
                    for insight in data["insights"]:
                         insights.append(f"- From {data.get('filename', 'Unknown')}: {insight}")
            except:
                pass
        return insights

class AnalysisEngine:
    def __init__(self, api_key):
        self.api_key = api_key

    def analyze_video(self, video_obj, context_objs, filename, run_manager):
        # 1. Reset Context / Create New Client
        # We create a new client for each analysis to ensure a robust, fresh connection
        # and to strictly manage the context window (no history spillover).
        client = genai.Client(api_key=self.api_key, http_options={'timeout': 3600000})
        
        # 2. Gather Insights from the CURRENT run
        previous_insights = run_manager.get_previous_insights()
        insights_context = ""
        if previous_insights:
            insights_context = "\n\n**INSIGHTS GATHERED FROM PREVIOUS VIDEOS IN THIS RUN:**\n" + "\n".join(previous_insights)

        logging.info(f"Analyzing {filename}. Included {len(previous_insights)} prior insights.")

        prompt = f"""
        You are an expert legal analyst and video forensic investigator working for the defense of Mr. Vega.
        
        Your task is to deeply analyze the provided video footage ({filename}) in the context of the attached legal documents.
        
        {insights_context}

        **CRITICAL OBJECTIVE:** You must specifically identify and extract clips that assist in the defense of the disabled defendant (Mr. Vega). 
        
        **TIMESTAMPS AND CHRONOLOGY - CRITICAL:**
        1.  **ABSOLUTE FILE TIME ONLY:** All `start_time` and `end_time` values MUST use the time elapsed from the beginning of THIS video file (00:00).
        2.  **IGNORE BURNT-IN TIMESTAMPS:** Do NOT use the OSD (On-Screen Display) date/time text visible on the video (e.g., "2024-03-15..."). These are historical and do not correspond to the video player reference.
        3.  **CHRONOLOGICAL ORDER:** Ensure all extracted clips are listed in strictly chronological order based on the video file time.

        **SPECIFIC KEY MOMENTS TO LOOK FOR:**
        1.  **The 'Bail Out':** Locate the exact moment the female passenger exits the vehicle during the chase. Analyze the surroundings, specifically looking for a pickup truck parked across the street and any anomalies regarding her extraction.
        2.  **The Walker:** Find the clip where a walker is ejected from the fleeing vehicle.
        3.  **Foster/'Becker' Apprehension:** Analyze footage of Foster (or the individual identifying as 'Becker') at the end of the chase. Look for evidence of him faking an overdose and the interaction where he provides a false identity.
        4.  **Vega's Vulnerability & Integrity (Booking):** Look for scenes where Mr. Vega mentions his "heart hurting". **CRITICAL:** Interpret this carefully—it is likely metaphorical (heartbroken/sadness) rather than physical pain. Highlighting moments where he *rejects* the idea of being physically injured (e.g., refusing medical aid for fake injuries) is vital to show his **integrity** and honesty.
        5.  **The Purse Incident:** Find a specific moment where officers discuss taking a brand name purse home to a girlfriend/wife instead of logging it as evidence.
        6.  **Police Unprofessionalism:** Identify any instances of officers laughing, joking inappropriately, or mocking the situation/defendants.
        7.  **Suspicious Audio:** Note any moments where microphones appear to be manually muted or shut off suspiciously during sensitive conversations.

        **General Defense Priorities:**
        1.  Exculpatory evidence or contradictions to the prosecution's narrative.
        2.  Moments that display the defendant's disability, vulnerability, physical limitations, or confusion.
        3.  "Emotionally resonant" moments that humanize the defendant or could sway public/jury opinion in his favor.
        4.  Procedural errors, aggression, or lack of accommodation by law enforcement.

        Output the FINAL analysis in the following JSON format (do not include markdown formatting like ```json in the final output, just the raw JSON):
        {{
          "filename": "{filename}",
          "summary": "Brief summary of the video content",
          "clips": [
            {{
              "start_time": "MM:SS",
              "end_time": "MM:SS",
              "description": "Detailed description of what happens in this clip",
              "transcript": "Verbatim transcript of any dialogue (if audible)",
              "significance": "Explain explicitly how this helps the defense or sways opinion. Connect to specific context documents where possible."
            }}
          ],
          "insights": [
            "Key insight 1",
            "Key insight 2"
          ]
        }}
        """

        contents = [video_obj] + context_objs + [prompt]

        try:
            response = client.models.generate_content(
                model=MODEL_ID, 
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    thinking_config=types.ThinkingConfig(
                        include_thoughts=True
                    )
                )
            )

            # Extract thoughts and text
            thoughts = []
            json_text = ""
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    is_thought = False
                    if hasattr(part, 'thought') and part.thought:
                         is_thought = True
                    
                    if is_thought:
                        thoughts.append(part.text)
                    elif part.text:
                        json_text += part.text

            full_thought_process = "\n\n".join(thoughts)
            
            try:
                result = json.loads(json_text)
                result["thinking_process"] = full_thought_process
                return result
            except json.JSONDecodeError:
                logging.error(f"Failed to parse JSON from {filename}. Raw text: {json_text[:200]}...")
                return {
                    "filename": filename,
                    "error": "JSON Parse Error",
                    "raw_text": json_text,
                    "thinking_process": full_thought_process
                }

        except Exception as e:
            logging.error(f"Failed to analyze {filename}: {e}")
            return None

def main():
    parser = argparse.ArgumentParser(description="Multi-phase Video Analysis Tool")
    parser.add_argument("--interactive", action="store_true", help="Launch interactive upload manager")
    parser.add_argument("--run-id", type=str, help="Resume or specify a Run ID (e.g., run_20240101_120000)")
    parser.add_argument("--upload-only", action="store_true", help="Only perform uploads and exit")
    args = parser.parse_args()

    # Base Client for Uploads (AnalysisEngine creates its own)
    base_client = genai.Client(api_key=API_KEY, http_options={'timeout': 3600000}) 
    upload_manager = UploadManager(base_client)

    # PHASE 1: Uploads
    if args.interactive:
        upload_manager.interactive_menu()
        if args.upload_only:
            return

    # Ensure Uploads (Auto-mode if not interactive)
    logging.info("Checking file uploads...")
    video_files = sorted(glob.glob(os.path.join(VIDEO_DIR, "**/*.mp4"), recursive=True))
    for vf in video_files:
        upload_manager.upload_file_cached(vf, mime_type="video/mp4")
    
    context_files_objs = []
    pdf_paths = glob.glob(os.path.join(CONTEXT_DIR, "*.pdf"))
    if pdf_paths:
        for pdf_path in pdf_paths:
             f_obj = upload_manager.upload_file_cached(pdf_path, mime_type="application/pdf")
             if f_obj: context_files_objs.append(f_obj)

    if args.upload_only:
        logging.info("Upload-only mode complete. Exiting.")
        return

    # PHASE 2: Run State
    run_manager = RunManager(args.run_id)
    logging.info(f"Starting Analysis Phase. Outputting to: {run_manager.results_dir}")

    # PHASE 3: Analysis Loop
    analysis_engine = AnalysisEngine(API_KEY)
    processed_files = run_manager.get_processed_files()

    for video_path in video_files:
        filename = os.path.basename(video_path)
        
        if filename in processed_files:
            logging.info(f"Skipping {filename} (Already in {run_manager.results_dir})")
            continue

        # Get the remote file object for analysis (freshly fetched to ensure active)
        video_obj = upload_manager.upload_file_cached(video_path, mime_type="video/mp4")
        
        if video_obj:
            result = analysis_engine.analyze_video(video_obj, context_files_objs, filename, run_manager)
            
            if result:
                # Save Result
                out_path = os.path.join(run_manager.results_dir, f"{filename}.json")
                save_json_file(out_path, result)
                logging.info(f"Analysis complete for {filename}. Saved to {out_path}")
            else:
                logging.error(f"Analysis return None for {filename}")

    logging.info(f"Run {run_manager.run_id} complete.")

if __name__ == "__main__":
    main()
