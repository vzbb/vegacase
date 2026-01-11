import os
import json
import glob

# Constants
BASE_DIR = "/home/tt/gemmi"
CLIPS_ROOT = os.path.join(BASE_DIR, "dashboard/clips")
OUTPUT_JS = os.path.join(BASE_DIR, "dashboard/data.js")

def get_runs():
    """Scan dashboard/clips/ for run directories."""
    runs = []
    if os.path.exists(CLIPS_ROOT):
        items = os.listdir(CLIPS_ROOT)
        for item in items:
            full_path = os.path.join(CLIPS_ROOT, item)
            # We look for directories that start with "run_"
            if os.path.isdir(full_path) and item.startswith("run_"):
                runs.append(item)
    runs.sort(reverse=True) # Newest first
    return runs

def get_run_data(run_id):
    """Load clips_metadata.json from the run directory."""
    run_dir = os.path.join(CLIPS_ROOT, run_id)
    meta_path = os.path.join(run_dir, "clips_metadata.json")
    
    run_clips = []
    
    if os.path.exists(meta_path):
        try:
            with open(meta_path, 'r') as f:
                data = json.load(f)
                
            if isinstance(data, list):
                for clip in data:
                    # IMPORTANT: Prepend run_id to filename so app.js can find it
                    # app.js looks in "clips/", so we need "run_ID/file.mp4"
                    original_filename = clip.get('filename', '')
                    if original_filename:
                        clip['filename'] = f"{run_id}/{original_filename}"
                    
                    # Ensure ID is unique across runs if needed, though they are siloed
                    # clip['id'] is usually "clip_001", valid within the run scope.
                    
                    run_clips.append(clip)
            else:
                print(f"Warning: {meta_path} content is not a list.")
                
        except Exception as e:
            print(f"Error reading {meta_path}: {e}")
    else:
        print(f"Metadata not found for {run_id} at {meta_path}")
            
    return run_clips

def main():
    all_runs_data = {}
    runs = get_runs()
    
    print(f"Found processed runs in {CLIPS_ROOT}: {runs}")
    
    for run in runs:
        print(f"Processing {run}...")
        clips = get_run_data(run)
        if clips:
            all_runs_data[run] = clips
            print(f"  Loaded {len(clips)} clips.")
        else:
            print(f"  No clips found.")
            
    # Write to JS
    js_content = f"const MULTI_RUN_DATA = {json.dumps(all_runs_data, indent=2)};\n"
    
    with open(OUTPUT_JS, 'w') as f:
        f.write(js_content)
        
    print(f"\nSuccess! Wrote {len(all_runs_data)} runs to {OUTPUT_JS}")

if __name__ == "__main__":
    main()
