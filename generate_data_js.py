import json
import os

base_dir = "/home/tt/gemmi"
json_path = os.path.join(base_dir, "clips/clips_metadata.json")
js_path = os.path.join(base_dir, "dashboard/data.js")

if os.path.exists(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    js_content = f"const CLIPS_DATA = {json.dumps(data, indent=2)};"
    
    with open(js_path, 'w') as f:
        f.write(js_content)
    
    print(f"Generated {js_path} with {len(data)} items.")
else:
    print(f"Error: {json_path} not found.")
