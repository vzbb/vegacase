import json
import os
import subprocess
import re
import datetime
import glob

def parse_time(t_str):
    try:
        parts = list(map(float, t_str.split(':')))
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        elif len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
    except ValueError:
        pass
    return 0

def get_video_duration(path):
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', path]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return float(result.stdout.strip())
    except Exception as e:
        print(f"Error getting duration for {path}: {e}")
        return 0

def parse_filename_time(filename):
    # Pattern for Axon: ...YYYY-MM-DD_HHMM...
    match = re.search(r'(\d{4}-\d{2}-\d{2})_(\d{2})(\d{2})', filename)
    if match:
        date_str = match.group(1)
        hr = int(match.group(2))
        mn = int(match.group(3))
        # We handle basic HH:MM.
        return hr * 3600 + mn * 60
    return None

def get_part_info(filename):
    """Extracts base name and part number if filename follows 'PartXXX' pattern."""
    match = re.search(r'^(.*?)(_Part(\d+))\.mp4$', filename)
    if match:
        return match.group(1), int(match.group(3))
    return None, None

def process_run(src_path, out_dir, video_dir, log_f):
    def log(msg):
        print(msg)
        log_f.write(msg + "\n")

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    data = []
    if os.path.isdir(src_path):
        log(f"Loading JSONs from directory: {src_path}")
        json_files = glob.glob(os.path.join(src_path, "*.json"))
        for jf in json_files:
            try:
                with open(jf, 'r') as f:
                    content = json.load(f)
                    if isinstance(content, list):
                        data.extend(content)
                    elif isinstance(content, dict):
                        data.append(content)
            except Exception as e:
                log(f"Error reading {jf}: {e}")
    else:
        log(f"Loading single JSON/File: {src_path}")
        if os.path.isfile(src_path):
            with open(src_path, 'r') as f:
                data = json.load(f)

    if not data:
        log("No data found to process.")
        return

    # Prep: Identify partitioned sequences and their durations
    # Map: base_name -> {part_num: duration}
    part_durations = {}
    for entry in data:
        fname = entry.get('filename')
        if not fname: continue
        base, part = get_part_info(fname)
        if base is not None:
            if base not in part_durations:
                part_durations[base] = {}
            fpath = os.path.join(video_dir, fname)
            if os.path.exists(fpath):
                part_durations[base][part] = get_video_duration(fpath)

    output_data = []
    clip_counter = 0
    log(f"Starting processing. Found {len(data)} source video entries.")

    for entry in data:
        src_filename = entry.get('filename')
        src_file_path = os.path.join(video_dir, src_filename)
        
        if not os.path.exists(src_file_path):
            log(f"WARNING: Source video not found: {src_file_path}")
            continue
            
        log(f"Processing videos from: {src_filename}")
        
        # Get actual duration
        video_duration = get_video_duration(src_file_path)
        if video_duration == 0:
            log("  Failed to get video duration. Skipping.")
            continue
            
        # Get filename time offset if needed
        filename_start_sec = parse_filename_time(src_filename)
        
        # Calculate cumulative offset for partitioned videos
        base, part_num = get_part_info(src_filename)
        cumulative_part_offset = 0
        if base and part_num and base in part_durations:
            for p in range(part_num):
                cumulative_part_offset += part_durations[base].get(p, 0)
            if cumulative_part_offset > 0:
                log(f"  Detected sequence: {base}. Part {part_num} starts at +{cumulative_part_offset:.1f}s")
            
        clips = entry.get('clips', [])
        for clip in clips:
            clip_counter += 1
            start_str = clip.get('start_time', '0:00')
            end_str = clip.get('end_time', '0:00')
            
            start_sec = parse_time(start_str)
            end_sec = parse_time(end_str)
            
            # Check if timestamp is absolute (burnt-in)
            if start_sec > (video_duration + cumulative_part_offset) and start_sec > 3600:
                if filename_start_sec:
                    # The absolute OSD time minus the start of the ENTIRE sequence
                    diff = start_sec - filename_start_sec
                    # Now subtract the time elapsed in previous parts to get relative time in THIS part
                    relative_diff = diff - cumulative_part_offset
                    
                    if 0 <= relative_diff <= video_duration:
                        log(f"  Adjusting OSD {start_str}: Total sequence diff {diff}s -> Partition relative {relative_diff:.1f}s")
                        end_diff = (end_sec - filename_start_sec) - cumulative_part_offset
                        start_sec = relative_diff
                        end_sec = end_diff
                    else:
                        # Only log if it's REALLY outside the total duration of THIS part
                        log(f"  Timestamp {start_str} (Diff: {diff}s) outside partition {src_filename} bounds (Relative: {relative_diff:.1f}s, Dur: {video_duration}s). Skipping.")
                        continue
                else:
                     log(f"  Timestamp {start_str} > Duration and no filename date parsing possible. Skipping.")
                     continue

            # Basic validation
            if start_sec >= video_duration:
                 log(f"  Start time {start_sec} beyond video length {video_duration}. Skipping.")
                 continue
                 
            if end_sec > video_duration:
                 log(f"  End time {end_sec} clipped to video length {video_duration}.")
                 end_sec = video_duration

            duration = end_sec - start_sec
            
            if duration <= 1:
                log(f"  Skipping short/invalid clip: {start_str} to {end_str} (Dur: {duration})")
                continue
                
            clip_id = f"clip_{clip_counter:03d}"
            out_filename = f"{clip_id}.mp4"
            out_path = os.path.join(out_dir, out_filename)
            
            fade_out_start = max(0, duration - 0.5)
            vf = f"fade=t=in:st=0:d=0.3,fade=t=out:st={fade_out_start}:d=0.5"
            af = f"loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:ss=0:d=0.3,afade=t=out:st={fade_out_start}:d=0.5"
            
            cmd = [
                'ffmpeg', '-y',
                '-ss', str(start_sec),
                '-t', str(duration),
                '-i', src_file_path,
                '-map', '0:v:0', '-map', '0:a:0',
                '-filter:v', vf,
                '-filter:a', af,
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '22',
                '-c:a', 'aac', '-b:a', '192k',
                out_path
            ]
            
            log(f"  [{clip_id}] Extracting {start_sec:.1f}-{end_sec:.1f} ({duration:.1f}s)...")
            try:
                res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
                if res.returncode != 0:
                    log(f"  Error processing clip {clip_id}: {res.stderr[-200:]}")
                else:
                    meta = clip.copy()
                    meta['id'] = clip_id
                    meta['filename'] = out_filename
                    meta['original_video'] = src_filename
                    meta['duration_seconds'] = duration
                    meta['parent_summary'] = entry.get('summary', '')
                    output_data.append(meta)
            except Exception as e:
                log(f"  Exception: {e}")

    # Save the map
    meta_json_path = os.path.join(out_dir, "clips_metadata.json")
    with open(meta_json_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    log(f"Finished Run. Metadata saved to {meta_json_path}")

def main():
    base_dir = "/home/tt/gemmi"
    video_dir = os.path.join(base_dir, "video")
    results_root = os.path.join(base_dir, "results")
    dashboard_clips_root = os.path.join(base_dir, "dashboard/clips")
    log_file = os.path.join(base_dir, "processing.log")

    if not os.path.exists(dashboard_clips_root):
        os.makedirs(dashboard_clips_root)

    with open(log_file, 'w') as log_f:
        print(f"Scanning for runs in {results_root}...")
        runs = [d for d in os.listdir(results_root) if os.path.isdir(os.path.join(results_root, d))]
        runs.sort() # Process in order

        for run_name in runs:
            out_dir = os.path.join(dashboard_clips_root, run_name)
            if os.path.exists(out_dir):
                msg = f"Skipping Run: {run_name} (already exists in {dashboard_clips_root})"
                print(msg)
                log_f.write(msg + "\n")
                continue

            print(f"\n>>> Processing Run: {run_name}")
            log_f.write(f"\n>>> Processing Run: {run_name}\n")
            src_path = os.path.join(results_root, run_name)
            process_run(src_path, out_dir, video_dir, log_f)

    print(f"\nAll runs processed. Log saved to {log_file}")

if __name__ == "__main__":
    main()
