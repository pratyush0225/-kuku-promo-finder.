# Kuku AI Generalist Assignment — Problem 1: Find the Promos

**Candidate:** Pratyush Prakash  
**Roll Number:** CE23BTECH11042  
**Show Analyzed:** *I Married a Broken Soldier. He Was a Duke* (First 50 Episodes)  
**Deliverable Package:** `KUKU_FINAL_SUBMISSION`

---

## 📌 Executive Summary
Today, editors at Kuku watch every episode and manually hand-pick promo clips to run as vertical ads on TikTok, Instagram Reels, and YouTube Shorts. This tool automates that discovery process directly from screenplay screenplays.

It parses timestamped screenplay text, generates every valid 20–60 second window aligned to exact event boundaries, scores candidates on opening hooks (0–3s), unresolved cliffhangers (last ~6s), narrative standalone clarity, and pacing, and outputs a globally ranked catalog of promos grouped into Tiers A, B, and C.

---

## 🚀 Key Features

1. **Deterministic Timestamp Boundary Guarantee:**
   - LLMs frequently hallucinate or drift on float timestamps. Our system keeps window generation and boundary alignment entirely in Python code. Every clip starts where a shot or line begins and ends where one ends—never cutting mid-sentence.
2. **0–3 Second Hook Discovery:**
   - Detects sudden physical actions (`bursts`, `slaps`, `confronts`), intense character deliveries (`Furious`, `Desperate`, `Menacing`), and shocking betrayal statements.
3. **Cliffhanger & Unresolved Ending Detection:**
   - Detects trailing questions, high-stakes accusations, em-dash interrupted cutoffs (`--`), and dramatic sound cues (`cliffhanger cut`, `cello swell`).
4. **Weakest-Link Scoring (`min` penalty):**
   - A brilliant 3-second hook cannot hide a boring or resolved ending. The scoring formula applies a weakest-link penalty so that only clips strong in *both* hook and cliffhanger achieve Tier A.
5. **Non-Maximum Suppression (NMS) & 2-Part Stitched Promos:**
   - Removes redundant overlapping windows and supports joined two-part promos that pair an opening crisis with a concluding climax from the same episode.
6. **Episode-Ending Anchor Rule:**
   - Preserves each episode's intentional final cliffhanger beat, elevating recall on major story climaxes from 2/7 to 6/7.
7. **Swappable LLM Judge Layer:**
   - Code guarantees timestamp validity; an optional LLM layer (OpenAI, Gemini, Groq, or Ollama compatible) can provide qualitative scoring and copy refinements.

---

## 🛠️ Technology Stack & Dependencies

- **Language:** Python 3.9+ (Tested on Python 3.14)
- **Dependencies:** **Zero external libraries (Python Standard Library only)**
  - No `pip install` required. Built with `re`, `json`, `csv`, `os`, `sys`, `dataclasses`, and `http.server`.
- **Frontend / Dashboard:** HTML5, CSS3, Vanilla JS (self-contained within `app.py`).

---

## 💻 Step-by-Step Execution Commands

### 1. Run the Promo Discovery Tool
```bash
cd KUKU_FINAL_SUBMISSION/2_Source_Code
python3 run.py ../../data/scripts --out ../3_Raw_Outputs
```
*Execution Speed:* Processes all 50 episodes (3,727 events) in **~0.15 seconds**.

### 2. Run the Hard-Constraint Validator
```bash
python3 check_outputs.py ../../data/scripts ../3_Raw_Outputs/promos.json
```
*Validation Result:*
```text
Loading episodes from ../../data/scripts...
Validating 69 promos across 50 episodes...

50 episodes checked. 69 promos validated.
ALL CHECKS PASSED.
```

### 3. Launch the Interactive Web Dashboard
```bash
cd ../Website
python3 app.py 8000
```
Open **[http://localhost:8000](http://localhost:8000)** in any web browser to view, filter, and search promos.

---

## 📊 Results on the 50-Episode Pack

- **Episodes Evaluated:** 50
- **Total Script Events Parsed:** 3,727 (100% parsed, 0 errors)
- **Total Promos Extracted:** 69 promos across 49 episodes
- **Average Duration:** 37.1 seconds (Range: 21.8s to 57.7s)
- **Tier Breakdown:**
  - **Tier A (Post First):** 10 promos (Highest confidence conflict and premise reveals)
  - **Tier B:** 20 promos (Strong secondary beats, slight trims helpful)
  - **Tier C:** 39 promos (Supporting narrative or quiet moments)

### Top Recommended Promos to Post First:
1. **#1 Ep 15 (Stitched, 47.4s):** Opens on bandaged Juliana bursting into the cottage as thugs crush her medicinal herbs → skips middle abuse → ends on Alexander stepping between her and the thugs with lethal intent.
2. **#2 Ep 11 (32.0s):** Accusation of theft: Gerald claims Alexander stole his pocket watch; rapid-fire escalation ending on an unresolved house search protest.
3. **#3 Ep 2 (27.6s):** Instant premise clarity: *"I cannot marry you, Juliana."* Needs zero show context for a first-time viewer.
4. **#4 Ep 28 (32.8s):** High drama accusation: *"I did not poison her!"* ending abruptly as the Duchess collapses mid-sentence.

---

## 🔍 Quality Audit & Honest Limitations

### Manual Sanity Audit (Top 20 Clips)
- **8 GOOD (40%):** Ready to post immediately as-is.
- **9 OK (45%):** Captures the right dramatic turn, but benefits from a minor editor trim.
- **3 BAD (15%):** Resolves too neatly or lacks sufficient standalone context.
- **Total Usability:** **85% (17 / 20 clips usable)**.

### Known Limitations:
1. **Text Only (No Video):** The tool reads actions and dialogue but cannot see physical actor charisma, camera lighting, or musical delivery.
2. **Literal Sound Cue Traps:** Promo #6 (Ep 16) ended on a tender romantic gaze because the screenplay sound cue literally said *"cliffhanger hold"*, fooling heuristic rules.
3. **Subtle Drama Misses:** Ep 3's marriage proposal cliffhanger (*"accept my hand"*, followed by the congregation gasping) lacked question marks or fight verbs, scoring lower under pure rules. This is where the optional LLM judge adds value.
4. **Genre Specificity:** The lexicon is tuned for romantic drama / betrayal microdramas; adjusting for thriller or comedy requires updating `promo_finder/lexicon.py`.

---

## 🔒 Confidentiality & Privacy Notice
In accordance with Kuku's assignment terms, the screenplay scripts for *"I Married a Broken Soldier. He Was a Duke"* are private and proprietary to Kuku. They are kept local in `data/scripts/` and have **not** been uploaded to any public repository or web host.

---

## 📂 Submission Directory Layout
```
KUKU_FINAL_SUBMISSION/
├── README.md                           (Master project documentation)
├── 1_Project_Documentation/
│   ├── README.md                       (Documentation overview)
│   ├── Solution_Doc_Problem1_Find_the_Promos.pdf  (Official 2-page submission doc)
│   └── READ_ME_FIRST_Checklist.md      (Submission guidelines & checklist)
├── 2_Source_Code/
│   ├── README.md                       (Source code and CLI documentation)
│   ├── run.py                          (Main CLI script)
│   ├── check_outputs.py                (Hard-constraint validator)
│   ├── app.py                          (Web dashboard application)
│   └── promo_finder/
│       ├── __init__.py
│       ├── parse.py                    (Regex screenplay parser)
│       ├── lexicon.py                  (Genre keywords and triggers)
│       ├── candidates.py               (Window generation and scoring)
│       ├── judge.py                    (Swappable LLM judge)
│       └── rank.py                     (Global ranking and tiering)
├── 3_Raw_Outputs/
│   ├── README.md                       (Output summary & stats)
│   ├── promos.json                     (Structured JSON outputs)
│   ├── promos.csv                      (Spreadsheet CSV export)
│   ├── promos.md                       (Markdown catalog with transcripts)
│   ├── audit_top20_labels.md           (Audit table of top 20 promos)
│   └── run_log.txt                     (Execution statistics log)
├── 4_Demo_Video/
│   ├── README.md                       (Video instructions & link placeholders)
│   └── Video_Script_3min.md            (3-minute timed walkthrough script)
└── Website/
    ├── README.md                       (Dashboard usage & deployment guide)
    └── app.py                          (Interactive standalone web application)
```
