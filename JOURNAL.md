# Journal - 2026-01-11

## Tasks
- Reindex clips in dashboard/clips/ after deleting clip_008.
- Update dashboard/clips/clips_metadata.json (decrement IDs 009-048 by 1).
- Rename files in dashboard/clips/ (decrement IDs 009-048 by 1).

## Progress
- 09:41 Started reindexing task.

## Completion - 09:42
- Reindexed clips 009-048 to 008-047.
- Updated dashboard/clips/clips_metadata.json: 40 entries modified.
- Renamed 40 .mp4 files in dashboard/clips/.
- Verified JSON and filesystem consistency.

## 09:55 AM
Starting modification of `process_clips.py` to handle multiple runs.
- Source: `/home/tt/gemmi/results/` (all subdirectories)
- Destination: `/home/tt/gemmi/dashboard/clips/<run_name>/`
- Each run will have its own isolated clips and `clips_metadata.json`.
- `clip_counter` will reset per run to maintain consistent numbering within each run.
- Added logic to skip runs that have already been processed (checks for existing subdir in `dashboard/clips/`).
