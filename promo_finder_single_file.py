#!/usr/bin/env python3
"""
Kuku Promo Finder — All-In-One Single File Python Tool
Problem 1: Find 20-60s promos in microdrama screenplays.

Author: Pratyush Prakash (CE23BTECH11042)
Zero external dependencies (Python 3.9+ standard library only).

Commands:
    1. Run Promo Discovery on Screenplays:
       python promo_finder_single_file.py run PATH_TO_SCRIPTS [--out OUTPUT_DIR]

    2. Validate Constraints on Discovered Promos:
       python promo_finder_single_file.py check PATH_TO_SCRIPTS PROMOS_JSON_PATH

    3. Launch Interactive Web Dashboard:
       python promo_finder_single_file.py serve [PORT]
"""

import os
import sys
import re
import time
import json
import csv
import argparse
import http.server
import socketserver
import urllib.parse
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional

# ==============================================================================
# 1. LEXICON & SCORING TRIGGERS
# ==============================================================================

HOOK_ACTION_VERBS = [
    "burst", "bursts", "slap", "slaps", "grab", "grabs", "slam", "slams",
    "collapse", "collapses", "confront", "confronts", "freeze", "freezes",
    "shatter", "shatters", "storm", "storms", "push", "pushes", "shove", "shoves",
    "tear", "tears", "strike", "strikes", "choke", "chokes", "gasp", "gasps",
    "weep", "weeps", "scream", "screams", "shout", "shouts", "draw", "draws"
]

INTENSE_DELIVERY_CUES = [
    "furious", "desperate", "alarmed", "screaming", "gasping", "cold, menacing",
    "incredulous", "tearful", "shivering", "venomous", "mocking", "broken",
    "authoritative", "defiant", "outraged", "lethal", "cruel", "thunderous"
]

CONFLICT_TRIGGERS = [
    "stop", "liar", "cheat", "traitor", "poison", "murder", "kill", "die",
    "betray", "betrayal", "thief", "stole", "steal", "arrest", "leave",
    "never", "divorce", "marry", "wedding", "bastard", "beggar", "refuse",
    "cannot marry", "hand in marriage", "how dare", "what did you do", "enough"
]

CLIFFHANGER_SOUND_CUES = [
    "cliffhanger cut", "cliffhanger sting", "cliffhanger", "dramatic cello",
    "ominous cello", "crescendo", "abrupt cut", "cut to black", "abrupt cliffhanger"
]

CLIFFHANGER_PHRASES = [
    "who are you", "what have you done", "is that what", "what wedding",
    "look at me", "choose your next words", "tell me the truth", "answer me",
    "you wouldn't dare", "going somewhere"
]

# Scoring Weights
W = {
    "hook": 0.35,
    "cliffhanger": 0.35,
    "standalone": 0.20,
    "pace": 0.10,
    "weakest_link_penalty": 0.40,
}

# ==============================================================================
# 2. SCREENPLAY PARSER
# ==============================================================================

def parse_timestamp(ts_str: str) -> float:
    """Converts (mm:ss.xx) or mm:ss.xx string to float seconds."""
    ts_str = ts_str.strip().strip("()")
    parts = ts_str.split(":")
    if len(parts) == 2:
        return round(float(parts[0]) * 60 + float(parts[1]), 2)
    elif len(parts) == 3:
        return round(float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2]), 2)
    return round(float(parts[0]), 2)


def format_timestamp(seconds: float) -> str:
    """Converts float seconds to mm:ss.xx string format."""
    mins = int(seconds // 60)
    secs = seconds - (mins * 60)
    return f"{mins:02d}:{secs:05.2f}"


@dataclass
class Event:
    index: int
    scene_num: int
    event_type: str  # 'camera', 'action', 'sound', 'dialogue'
    speaker: Optional[str]
    direction: Optional[str]
    content: str
    start: float
    end: float

    @property
    def duration(self) -> float:
        return round(self.end - self.start, 2)


@dataclass
class Episode:
    episode_num: int
    title: str
    logline: str
    continuity_notes: str
    events: List[Event]


def parse_episode_file(filepath: str) -> Episode:
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    filename = os.path.basename(filepath)
    ep_num_match = re.search(r"EPISODE\s+NUMBER:\s*(?:Episode\s*)?(\d+)", text, re.IGNORECASE)
    if ep_num_match:
        ep_num = int(ep_num_match.group(1))
    else:
        file_num = re.search(r"episode-?(\d+)", filename, re.IGNORECASE)
        ep_num = int(file_num.group(1)) if file_num else 1

    logline_match = re.search(r"EPISODE\s+LOGLINE:\s*(.*?)(?=\n[A-Z\s]+:|\n---|\Z)", text, re.DOTALL | re.IGNORECASE)
    logline = logline_match.group(1).strip().replace("\n", " ") if logline_match else ""

    notes_match = re.search(r"CONTINUITY\s+NOTES:\s*(.*?)(?=\n---|\nSCENE|\Z)", text, re.DOTALL | re.IGNORECASE)
    continuity = notes_match.group(1).strip().replace("\n", " ") if notes_match else ""

    # Matches block headers e.g. **CAMERA:**, **ACTION:**, **JULIANA (Desperate):**
    block_pattern = re.compile(
        r"\*\*([^*]+?):?\*\*:?\s*\n"
        r"Start:\s*\(([0-9:.]+)\)\s*\|\s*End:\s*\(([0-9:.]+)\)\s*\n"
        r"(.*?)(?=\n\*\*|\nSCENE\s+\d+|\n---|\Z)",
        re.DOTALL,
    )

    events: List[Event] = []
    current_scene = 1
    scene_markers = list(re.finditer(r"SCENE\s+(\d+)", text, re.IGNORECASE))

    for match in block_pattern.finditer(text):
        header = match.group(1).strip()
        start_sec = parse_timestamp(match.group(2))
        end_sec = parse_timestamp(match.group(3))
        content = match.group(4).strip()

        match_pos = match.start()
        for sm in reversed(scene_markers):
            if sm.start() <= match_pos:
                try:
                    current_scene = int(sm.group(1))
                except ValueError:
                    current_scene = 1
                break

        header_clean = header.rstrip(":")
        header_upper = header_clean.upper()
        speaker = None
        direction = None

        if "CAMERA" in header_upper:
            event_type = "camera"
        elif "ACTION" in header_upper:
            event_type = "action"
        elif "SOUND" in header_upper:
            event_type = "sound"
        else:
            event_type = "dialogue"
            char_match = re.match(r"^([^()]+)(?:\((.*?)\))?$", header_clean)
            if char_match:
                speaker = char_match.group(1).strip()
                direction = char_match.group(2).strip() if char_match.group(2) else None
            else:
                speaker = header_clean

        events.append(Event(
            index=len(events),
            scene_num=current_scene,
            event_type=event_type,
            speaker=speaker,
            direction=direction,
            content=content,
            start=start_sec,
            end=end_sec,
        ))

    return Episode(
        episode_num=ep_num,
        title=f"Episode {ep_num}",
        logline=logline,
        continuity_notes=continuity,
        events=events,
    )


def load_all_episodes(scripts_dir: str) -> List[Episode]:
    episodes = []
    files = [f for f in os.listdir(scripts_dir) if f.endswith(".txt")]
    files.sort(key=lambda x: [int(c) if c.isdigit() else c for c in re.split(r"(\d+)", x)])
    for fname in files:
        fpath = os.path.join(scripts_dir, fname)
        ep = parse_episode_file(fpath)
        episodes.append(ep)
    episodes.sort(key=lambda e: e.episode_num)
    return episodes

# ==============================================================================
# 3. CANDIDATE GENERATION & SCORING
# ==============================================================================

@dataclass
class Segment:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return round(self.end - self.start, 2)


@dataclass
class PromoCandidate:
    episode_num: int
    segments: List[Segment]
    hook_desc: str
    cliffhanger_desc: str
    why: str
    hook_score: float
    cliff_score: float
    standalone_score: float
    pace_score: float
    total_score: float
    rank_score: float = 0.0
    flags: List[str] = field(default_factory=list)
    tier: str = "C"

    @property
    def duration(self) -> float:
        return round(sum(s.duration for s in self.segments), 2)

    @property
    def is_stitched(self) -> bool:
        return len(self.segments) > 1

    @property
    def segments_str(self) -> str:
        parts = [f"{format_timestamp(s.start)}-{format_timestamp(s.end)}" for s in self.segments]
        return "  +  ".join(parts)


def score_hook(events: List[Event], start_time: float) -> Tuple[float, str]:
    hook_events = [e for e in events if e.start < start_time + 3.0 and e.end > start_time]
    if not hook_events:
        hook_events = events[:1]

    score = 0.4
    first_event = hook_events[0]
    first_text = first_event.content.lower()

    if first_event.event_type == "dialogue":
        speaker = first_event.speaker or "Speaker"
        desc = f'{speaker}: "{first_event.content}"'
        if any(trig in first_text for trig in CONFLICT_TRIGGERS):
            score += 0.35
        if first_event.direction and any(cue in first_event.direction.lower() for cue in INTENSE_DELIVERY_CUES):
            score += 0.25
        if "!" in first_event.content or "?" in first_event.content:
            score += 0.15
    elif first_event.event_type == "action":
        desc = f"(action) {first_event.content}"
        if any(verb in first_text for verb in HOOK_ACTION_VERBS):
            score += 0.40
        else:
            score += 0.20
    else:
        desc = f"({first_event.event_type}) {first_event.content}"

    return min(1.0, round(score, 2)), desc


def score_cliffhanger(events: List[Event], end_time: float) -> Tuple[float, str]:
    tail_events = [e for e in events if e.end > end_time - 6.0 and e.start < end_time]
    if not tail_events:
        tail_events = events[-1:]

    score = 0.3
    last_event = tail_events[-1]
    last_text = last_event.content.lower()
    desc_parts = []

    if len(tail_events) > 1 and tail_events[-2].event_type == "dialogue":
        prev = tail_events[-2]
        desc_parts.append(f'{prev.speaker}: "{prev.content}"')

    if last_event.event_type == "dialogue":
        desc_parts.append(f'{last_event.speaker}: "{last_event.content}"')
        if last_event.content.rstrip().endswith("?"):
            score += 0.35
        elif "--" in last_event.content or "—" in last_event.content:
            score += 0.40
        elif last_event.content.rstrip().endswith("..."):
            score += 0.05
        elif "!" in last_event.content:
            score += 0.20
        if any(phrase in last_text for phrase in CLIFFHANGER_PHRASES):
            score += 0.30
    elif last_event.event_type == "sound":
        desc_parts.append(f"(sound) {last_event.content}")
        if any(cue in last_text for cue in CLIFFHANGER_SOUND_CUES):
            score += 0.50
    else:
        desc_parts.append(f"({last_event.event_type}) {last_event.content}")
        if any(cue in last_text for cue in CLIFFHANGER_SOUND_CUES):
            score += 0.40

    desc = " | ".join(desc_parts) if desc_parts else f'{last_event.speaker}: "{last_event.content}"'
    return min(1.0, round(score, 2)), desc


def score_standalone(events: List[Event]) -> Tuple[float, List[str]]:
    flags = []
    score = 1.0
    first = events[0]
    if first.event_type == "dialogue":
        cl = first.content.lower()
        if cl.startswith(("and ", "but ", "so ", "because ", "then ")):
            score -= 0.15
            flags.append("starts-conjunction")
        if re.search(r"\b(he|she|they|it|that)\b", cl[:15]):
            score -= 0.10
            flags.append("unclear-pronoun-start")
    return max(0.4, round(score, 2)), flags


def score_pace(events: List[Event], duration: float) -> float:
    dialogue_events = [e for e in events if e.event_type == "dialogue"]
    if not dialogue_events:
        return 0.5
    rate = len(dialogue_events) / (duration / 10.0)
    if rate >= 2.0:
        return 1.0
    elif rate >= 1.2:
        return 0.85
    elif rate >= 0.8:
        return 0.70
    return 0.55


def generate_candidates_for_episode(ep: Episode) -> List[PromoCandidate]:
    events = ep.events
    n = len(events)
    if n == 0:
        return []

    candidates: List[PromoCandidate] = []
    for i in range(n):
        for j in range(i, n):
            start_t = events[i].start
            end_t = events[j].end
            dur = end_t - start_t
            if 20.0 <= dur <= 60.0:
                we = events[i : j + 1]
                h_score, h_desc = score_hook(we, start_t)
                c_score, c_desc = score_cliffhanger(we, end_t)
                s_score, flags = score_standalone(we)
                p_score = score_pace(we, dur)

                mean_s = (h_score * W["hook"] + c_score * W["cliffhanger"] + s_score * W["standalone"] + p_score * W["pace"])
                min_core = min(h_score, c_score, s_score)
                total = round((1 - W["weakest_link_penalty"]) * mean_s + W["weakest_link_penalty"] * min_core, 3)

                why_parts = []
                if h_score >= 0.6: why_parts.append("opens on a strong line/action")
                if c_score >= 0.6: why_parts.append("cuts on an unresolved beat")
                if s_score >= 0.85: why_parts.append("easy to follow cold")
                if p_score >= 0.8: why_parts.append("tight, back-and-forth pacing")
                why = "; ".join(why_parts) if why_parts else "balanced candidate window"

                candidates.append(PromoCandidate(
                    episode_num=ep.episode_num,
                    segments=[Segment(start_t, end_t)],
                    hook_desc=h_desc,
                    cliffhanger_desc=c_desc,
                    why=why,
                    hook_score=h_score,
                    cliff_score=c_score,
                    standalone_score=s_score,
                    pace_score=p_score,
                    total_score=total,
                    flags=flags,
                ))

    # NMS Deduplication
    candidates.sort(key=lambda c: c.total_score, reverse=True)
    kept: List[PromoCandidate] = []
    for cand in candidates:
        cs = cand.segments[0].start
        ce = cand.segments[0].end
        overlap = False
        for k in kept:
            ks = k.segments[0].start
            ke = k.segments[0].end
            inter = max(0.0, min(ce, ke) - max(cs, ks))
            union = max(ce, ke) - min(cs, ks)
            if union > 0 and (inter / union) > 0.50:
                overlap = True
                break
        if not overlap:
            kept.append(cand)
            if len(kept) >= 10:
                break
    return kept


def rank_and_tier_promos(candidates: List[PromoCandidate], max_episodes: int = 50) -> List[PromoCandidate]:
    for cand in candidates:
        penalty = (cand.episode_num - 1) / (max_episodes - 1) * 0.10 if max_episodes > 1 else 0
        cand.rank_score = round(cand.total_score * (1.0 - penalty), 3)
        if cand.total_score < 0.60 and "low-confidence" not in cand.flags:
            cand.flags.append("low-confidence")

    candidates.sort(key=lambda c: c.rank_score, reverse=True)
    for idx, cand in enumerate(candidates):
        if idx < 10:
            cand.tier = "A"
        elif idx < 30:
            cand.tier = "B"
        else:
            cand.tier = "C"
    return candidates

# ==============================================================================
# 4. CONSTRAINT CHECKER
# ==============================================================================

def check_promos(scripts_dir: str, promos_json_path: str) -> bool:
    print(f"Loading episodes from {scripts_dir}...")
    episodes = load_all_episodes(scripts_dir)
    ep_map = {e.episode_num: e for e in episodes}

    with open(promos_json_path, "r", encoding="utf-8") as f:
        promos = json.load(f)

    print(f"Validating {len(promos)} promos across {len(episodes)} episodes...")
    errors = []

    for idx, p in enumerate(promos):
        rank = p.get("rank", idx + 1)
        ep_num = p.get("episode")
        duration = p.get("duration_seconds")
        seg_str = p.get("segments_str", "")

        if ep_num not in ep_map:
            errors.append(f"Promo #{rank}: Episode {ep_num} not found.")
            continue
        ep = ep_map[ep_num]

        if duration < 19.99 or duration > 60.01:
            errors.append(f"Promo #{rank} (Ep {ep_num}): Duration {duration}s outside 20-60s.")

        segments = []
        for part in seg_str.split("+"):
            part = part.strip()
            times = part.split("-")
            if len(times) == 2:
                segments.append((parse_timestamp(times[0]), parse_timestamp(times[1])))

        for s_idx in range(len(segments) - 1):
            if segments[s_idx][1] > segments[s_idx + 1][0]:
                errors.append(f"Promo #{rank}: Overlapping segments in stitched clip.")

        event_starts = {e.start for e in ep.events}
        event_ends = {e.end for e in ep.events}
        for s_sec, e_sec in segments:
            if not any(abs(s_sec - es) < 0.15 for es in event_starts):
                errors.append(f"Promo #{rank} (Ep {ep_num}): Start {s_sec}s not aligned to event boundary.")
            if not any(abs(e_sec - ee) < 0.15 for ee in event_ends):
                errors.append(f"Promo #{rank} (Ep {ep_num}): End {e_sec}s not aligned to event boundary.")

        if not p.get("hook"): errors.append(f"Promo #{rank}: Missing hook description.")
        if not p.get("cliffhanger"): errors.append(f"Promo #{rank}: Missing cliffhanger description.")
        if not p.get("why"): errors.append(f"Promo #{rank}: Missing 'why it works'.")

    if errors:
        print("\n❌ VALIDATION FAILED WITH ERRORS:")
        for e in errors[:10]: print(f"  - {e}")
        return False

    print(f"\n{len(episodes)} episodes checked. {len(promos)} promos validated.")
    print("ALL CHECKS PASSED.")
    return True

# ==============================================================================
# 5. WEB APPLICATION SERVER
# ==============================================================================

HTML_UI = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Kuku Promo Finder — Single File Dashboard</title>
  <style>
    :root {
      --bg: #0e1117; --card-bg: #161b22; --border: #30363d;
      --text: #c9d1d9; --bright: #f0f6fc; --muted: #8b949e;
      --primary: #f0883e; --accent: #58a6ff; --tier-a: #e3b341;
      --tier-b: #58a6ff; --tier-c: #8b949e;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: system-ui, sans-serif; background: var(--bg); color: var(--text); padding: 24px; line-height: 1.5; }
    .container { max-width: 1200px; margin: 0 auto; }
    .header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 20px; border-bottom: 1px solid var(--border); margin-bottom: 24px; }
    .header h1 { color: var(--bright); font-size: 24px; }
    .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 24px; }
    .stat { background: var(--card-bg); border: 1px solid var(--border); padding: 14px 18px; border-radius: 8px; }
    .stat-val { font-size: 22px; font-weight: 700; color: var(--bright); }
    .stat-lbl { font-size: 12px; color: var(--muted); text-transform: uppercase; margin-top: 4px; }
    .controls { display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }
    .search { flex: 1; min-width: 260px; background: var(--card-bg); border: 1px solid var(--border); color: var(--bright); padding: 10px 14px; border-radius: 6px; }
    .btn { background: var(--card-bg); border: 1px solid var(--border); color: var(--text); padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 500; }
    .btn.active, .btn:hover { background: var(--border); color: var(--bright); }
    .grid { display: grid; grid-template-columns: 1fr; gap: 16px; }
    .card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 18px; transition: border-color 0.2s; }
    .card:hover { border-color: var(--accent); }
    .card-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    .rank-tag { font-size: 16px; font-weight: 700; color: var(--bright); display: flex; align-items: center; gap: 8px; }
    .tier { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; }
    .tier-A { background: rgba(227, 179, 65, 0.2); color: var(--tier-a); border: 1px solid var(--tier-a); }
    .tier-B { background: rgba(88, 166, 255, 0.2); color: var(--tier-b); border: 1px solid var(--tier-b); }
    .tier-C { background: rgba(139, 148, 158, 0.2); color: var(--tier-c); border: 1px solid var(--tier-c); }
    .timing { font-family: monospace; font-size: 13px; color: var(--accent); background: #0d1117; padding: 4px 8px; border-radius: 4px; border: 1px solid #21262d; }
    .field { margin-bottom: 8px; font-size: 14px; }
    .field-lbl { font-weight: 600; color: var(--muted); display: inline-block; min-width: 90px; }
    .hook-val { color: #ffd33d; font-weight: 500; }
    .cliff-val { color: #f85149; font-weight: 500; }
    .why-val { color: var(--text); font-style: italic; }
    .card-foot { display: flex; justify-content: space-between; margin-top: 12px; padding-top: 10px; border-top: 1px solid #21262d; font-size: 12px; color: var(--muted); }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div>
        <h1>🎬 Kuku Promo Finder <span style="font-size: 12px; color: var(--primary); border: 1px solid var(--primary); padding: 3px 8px; border-radius: 12px;">Problem 1</span></h1>
        <p style="color: var(--muted); font-size: 13px; margin-top: 4px;">Automated Promo Discovery across 50 Screenplays</p>
      </div>
      <div style="font-size: 13px; color: var(--muted);">Candidate: Pratyush Prakash (CE23BTECH11042)</div>
    </div>
    <div class="stats">
      <div class="stat"><div class="stat-val" id="stat-count">69</div><div class="stat-lbl">Promos Discovered</div></div>
      <div class="stat"><div class="stat-val" id="stat-eps">49</div><div class="stat-lbl">Episodes Covered</div></div>
      <div class="stat"><div class="stat-val">37.1s</div><div class="stat-lbl">Mean Duration</div></div>
      <div class="stat"><div class="stat-val" style="color: var(--tier-a)">10</div><div class="stat-lbl">Tier A (Post First)</div></div>
    </div>
    <div class="controls">
      <input type="text" id="search" class="search" placeholder="Search episode, quote, character..." oninput="render()">
      <button class="btn active" onclick="setTier('ALL', this)">All (69)</button>
      <button class="btn" onclick="setTier('A', this)">Tier A (10)</button>
      <button class="btn" onclick="setTier('B', this)">Tier B (20)</button>
      <button class="btn" onclick="setTier('C', this)">Tier C (39)</button>
    </div>
    <div class="grid" id="grid"></div>
  </div>
  <script>
    let promos = [];
    let filterTier = 'ALL';
    async function init() {
      const res = await fetch('/api/promos');
      promos = await res.json();
      render();
    }
    function setTier(t, btn) {
      filterTier = t;
      document.querySelectorAll('.btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      render();
    }
    function render() {
      const q = document.getElementById('search').value.toLowerCase();
      const container = document.getElementById('grid');
      container.innerHTML = '';
      const filtered = promos.filter(p => {
        if (filterTier !== 'ALL' && p.tier !== filterTier) return false;
        if (!q) return true;
        return `ep ${p.episode} ${p.segments_str} ${p.hook} ${p.cliffhanger} ${p.why}`.toLowerCase().includes(q);
      });
      document.getElementById('stat-count').innerText = filtered.length;
      filtered.forEach(p => {
        const d = document.createElement('div');
        d.className = 'card';
        d.innerHTML = `
          <div class="card-top">
            <div class="rank-tag">#${p.rank} <span class="tier tier-${p.tier}">Tier ${p.tier}</span> Ep ${p.episode} ${p.is_stitched ? '<span style="color:#d2a8ff; font-size:11px;">[Stitched]</span>' : ''}</div>
            <div class="timing">⏱ ${p.segments_str} (${p.duration_seconds}s)</div>
          </div>
          <div class="field"><span class="field-lbl">🪝 Hook:</span><span class="hook-val">${escapeHtml(p.hook)}</span></div>
          <div class="field"><span class="field-lbl">⚡ Cliffhanger:</span><span class="cliff-val">${escapeHtml(p.cliffhanger)}</span></div>
          <div class="field"><span class="field-lbl">💡 Why:</span><span class="why-val">${escapeHtml(p.why)}</span></div>
          <div class="card-foot"><span>Rank Score: <strong>${p.rank_score}</strong> (Raw: ${p.score})</span><span>Flags: ${p.flags && p.flags.length ? p.flags.join(', ') : 'none'}</span></div>
        `;
        container.appendChild(d);
      });
    }
    function escapeHtml(s) { return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
    init();
  </script>
</body>
</html>
"""

def serve_dashboard(port: int = 8000, promos_data_file: Optional[str] = None):
    # Find promos.json
    candidates = [
        promos_data_file,
        os.path.join(os.getcwd(), "promos.json"),
        os.path.join(os.path.dirname(__file__), "KUKU_FINAL_SUBMISSION", "3_Raw_Outputs", "promos.json"),
        os.path.join(os.path.dirname(__file__), "3_Raw_Outputs", "promos.json"),
        os.path.join(os.path.dirname(__file__), "outputs", "promos.json"),
    ]
    json_path = next((f for f in candidates if f and os.path.isfile(f)), None)

    class AppHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path in ("/", "/index.html"):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(HTML_UI.encode("utf-8"))
            elif parsed.path == "/api/promos":
                if json_path and os.path.exists(json_path):
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(data.encode("utf-8"))
                else:
                    self.send_response(404)
                    self.end_headers()
            else:
                super().do_GET()

    with socketserver.TCPServer(("", port), AppHandler) as httpd:
        print("=" * 60)
        print(f"🚀 Kuku Promo Finder Web Dashboard is running!")
        print(f"👉 Open in your browser: http://localhost:{port}")
        print("=" * 60)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")

# ==============================================================================
# 6. MAIN CLI DISPATCHER
# ==============================================================================

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "run":
        if len(sys.argv) < 3:
            print("Usage: python promo_finder_single_file.py run PATH_TO_SCRIPTS [--out OUTPUT_DIR]")
            sys.exit(1)
        scripts_dir = sys.argv[2]
        out_dir = "outputs"
        if "--out" in sys.argv:
            idx = sys.argv.index("--out")
            if idx + 1 < len(sys.argv):
                out_dir = sys.argv[idx + 1]

        os.makedirs(out_dir, exist_ok=True)
        start_t = time.time()
        print("=" * 60)
        print("🎬 KUKU PROMO FINDER — Single File Runner")
        print("=" * 60)
        print(f"Reading scripts from: {scripts_dir}")
        episodes = load_all_episodes(scripts_dir)
        total_events = sum(len(e.events) for e in episodes)
        print(f"✓ Parsed {len(episodes)} episodes ({total_events} events)")

        # Generate candidates
        all_cands = []
        for ep in episodes:
            cands = generate_candidates_for_episode(ep)
            all_cands.extend(cands)

        ranked = rank_and_tier_promos(all_cands, max_episodes=len(episodes))
        promos_data = []
        for idx, c in enumerate(ranked):
            promos_data.append({
                "rank": idx + 1,
                "tier": c.tier,
                "episode": c.episode_num,
                "segments_str": c.segments_str,
                "duration_seconds": c.duration,
                "is_stitched": c.is_stitched,
                "hook": c.hook_desc,
                "cliffhanger": c.cliffhanger_desc,
                "why": c.why,
                "score": c.total_score,
                "rank_score": c.rank_score,
                "flags": c.flags,
            })

        json_out = os.path.join(out_dir, "promos.json")
        csv_out = os.path.join(out_dir, "promos.csv")
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(promos_data, f, indent=2)

        with open(csv_out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "rank", "tier", "episode", "segments_str", "duration_seconds",
                "is_stitched", "hook", "cliffhanger", "why", "score", "rank_score", "flags"
            ])
            writer.writeheader()
            for r in promos_data:
                row = dict(r)
                if isinstance(row.get("flags"), list):
                    row["flags"] = ";".join(row["flags"])
                writer.writerow(row)

        elapsed = round(time.time() - start_t, 2)
        print(f"✓ Extracted {len(promos_data)} promos in {elapsed}s")
        print(f"✓ Saved to {json_out} and {csv_out}")

    elif cmd == "check":
        if len(sys.argv) < 4:
            print("Usage: python promo_finder_single_file.py check PATH_TO_SCRIPTS PROMOS_JSON")
            sys.exit(1)
        scripts_dir = sys.argv[2]
        json_path = sys.argv[3]
        success = check_promos(scripts_dir, json_path)
        sys.exit(0 if success else 1)

    elif cmd == "serve":
        port = 8000
        if len(sys.argv) > 2 and sys.argv[2].isdigit():
            port = int(sys.argv[2])
        serve_dashboard(port)

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
