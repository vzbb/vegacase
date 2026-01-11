# Vega Defense - Video Evidence Dashboard

This dashboard visualizes the extracted video clips and forensic data.

## Usage

1. **Open the Dashboard**:
   Open `index.html` in your web browser. 
   
   ```bash
   xdg-open index.html
   ```

2. **Features**:
   - **Clip Grid**: Browse all extracted clips.
   - **Modal View**: Click any clip to view:
     - The video segment (with normalized audio and fades).
     - Full transcript.
     - Significance analysis.
     - Source metadata.

## Data Source
- Clips are stored in `../clips/`.
- Metadata is in `../clips/clips_metadata.json`.
- Source JSON: `../backup/analysis_results_final_run1.json`.

## Processing Details
- Audio: Normalized to EBU R128 (-16 LUFS) for consistent volume.
- Video: Fade-in (0.3s) and Fade-out (0.5s).
- Timestamps: Automatically corrected for relative/absolute time discrepancies.
