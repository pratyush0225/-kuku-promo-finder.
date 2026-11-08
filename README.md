# 3. Raw Outputs

This folder contains the complete, unedited output artifacts generated from running the Promo Discovery pipeline over the full 50-episode screenplay dataset (*"I Married a Broken Soldier. He Was a Duke"*).

## Summary Statistics
- **Total Screenplays Analyzed:** 50 episodes
- **Total Script Events Parsed:** 3,727 events
- **Promos Discovered:** 69 promos across 49 episodes
- **Clip Durations:** Mean 37.1s (Range: 21.8s – 57.7s)
- **Tier Breakdown:**
  - **Tier A (Post First):** 10 promos (Highest confidence, standalone, high conflict)
  - **Tier B:** 20 promos (Solid narrative beats, minor trim potential)
  - **Tier C:** 39 promos (Supporting clips, quiet episodes, or lower urgency)
- **Format Distribution:** 63 continuous clips, 6 two-part stitched promos

## Output Files

- **`promos.json`**  
  Full structured JSON output containing rank, tier, episode number, start/end timestamps, duration, hook, cliffhanger, 1-line rationale ("why it works"), composite score, rank score, and diagnostic flags.
- **`promos.csv`**  
  Tabular CSV export designed for video editors and marketing managers to quickly filter and import timestamps into editing software.
- **`promos.md`**  
  Human-readable Markdown catalog quoting the exact dialogue lines and action descriptions for each of the 69 candidate promo clips.
- **`audit_top20_labels.md`**  
  Manual sanity audit of the Top 20 ranked clips (8 Good / 9 OK / 3 Bad; 85% usable clips).
- **`run_log.txt`**  
  Machine execution log showing duration, episode coverage, and output paths.
