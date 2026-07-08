# Handoff — resume on your PC terminal

You're reading this because the repo is now synced onto your PC at
`Workout app/` (fast-forwarded to this same commit history — the local git repo
that used to hold only the original `CLAUDE.md` now has all of Phase 1 + 2).
This doc replaces anything I said earlier in chat — the chat won't follow you,
this file will.

## What's done (committed)

| Phase | State | Commits |
|-------|-------|---------|
| 1. Scaffold + constitution + Docker | ✅ done | `Scaffold repo, Docker, and secrets wiring` |
| Checkpoint 1: PDF/xlsx extraction proof | ✅ approved | (inspection only) |
| 2. Module B retriever (ingest + `/ask`) | ✅ done | `Add ingestion…`, `Add /ask endpoint…` |
| Checkpoint 2: live Hevy schema | ✅ approved 2026-07-08 | (probe run locally against real API) |
| 3. Module C Hevy normalization + summaries | ✅ done | `Add Hevy normalization, working weights, and summaries` |
| 4. Module A trainer wiring (`/chat`) | ⬜ **do this next** | |

**Checkpoint 2 findings (confirmed live):** exercise field is `title` (not
`name`), workout date lives in `start_time` (not `date`), weights are
`weight_kg` only. `app/hevy/normalize.py` maps these directly — see its
docstring. One live-data surprise: `weight_kg: 0` shows up for a few bodyweight
sets instead of `null` — treated as bodyweight (no working weight), not a
0 lb entry.

**Known gap for Module A:** none of the user's 318 logged workouts have RPE
recorded in Hevy (`rpe` is always `null`). The user is starting to log RPE in
Hevy going forward — Module A doesn't need special handling for the gap, just
expect `rpe: "-"` on older entries.

`docs/BUILD_PROMPT.md` has the original master prompt (moved there from
`CLAUDE.md`, which is now the short constitution). That's the source of truth
for scope.

## Local setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

Create `.env` (gitignored, never committed):

```
ANTHROPIC_API_KEY=
HEVY_API_KEY=   # from https://hevy.com/settings?developer — never commit it
```

**Note on `ANTHROPIC_API_KEY`:** this is billed separately from a Claude Pro
subscription — Pro doesn't include API credit, there's no way around that. You
don't need it for the very next step (the Hevy probe below calls only Hevy).
You do need it once you want real `/ask` or `/chat` answers instead of raw
retrieved data. Personal-use volume (a few questions a day) typically costs
cents-to-low-dollars a month. The default model in `app/config.py`
(`anthropic_model`) is `claude-opus-4-8` — the most capable and most expensive
tier; swap to `claude-haiku-4-5` (cheapest) or `claude-sonnet-5` (middle) there
if you want a lower ceiling before adding billing credit.

## `pdfs/` — you already have the real library, but two files are missing

Your local `pdfs/` folder has the full Nippard collection (way more than what I
worked with in the sandbox) — good, keep it. `.gitignore` already excludes it
from git.

**Missing: the two Excel workbooks.** They're what actually gets parsed for
structured sets/reps/RPE/rest data — the guidebook PDF's program tables are
rasterized images with no extractable text, so ingestion skips them and relies
entirely on the workbooks. You uploaded these to me directly in chat earlier:
- `The_Bodybuilding_Transformation_System__IntermediateAdvanced.xlsx`
- `The_Bodybuilding_Transformation_System__Beginner.xlsx`

Find them (wherever you originally downloaded/exported them) and drop them
into `pdfs/` before running ingest. Any `*.xlsx` / `*.pdf` in that folder is
picked up automatically — filenames don't matter.

## Verify Phase 2 works locally (with real embeddings)

The cloud run used an offline fallback embedder (HuggingFace was blocked
there). On your PC the default `sentence-transformers/all-MiniLM-L6-v2`
downloads on first use — semantic queries (e.g. "when should I deload?") will
match much better than the cloud run did.

```powershell
python -m app.retriever.ingest pdfs\
uvicorn app.main:app --port 8000
```
Then, in another shell:
```powershell
curl -X POST localhost:8000/ask -H 'content-type: application/json' `
  -d '{"question":"Sets, reps and RPE for the 45° Incline Barbell Press in Week 1?","program":"Intermediate-Advanced","week":1}'
```

Without `ANTHROPIC_API_KEY` set, this returns retrieved program data only (no
generated coaching text) — that's expected, not a bug.

## ▶ NEXT STEP — Checkpoint 2

Confirm the real Hevy schema before building normalization. This needs only
`HEVY_API_KEY`, not the Anthropic one:

```powershell
# HEVY_API_KEY is read from .env
python scripts\hevy_schema_probe.py
```

It prints field names/types for one workout + one routine. Compare against the
documented schema in the plan (workout sets: `weight_kg`, `reps`, `rpe`, set
`type`; routines: `rep_range {start,end}`, `rest_seconds`). If it matches,
Phase 3 can proceed as designed; if a field name differs, note it — only
`app/hevy/normalize.py` (not yet written) depends on it.

**Paste the probe output back into a Claude Code session pointed at this repo**
to continue — either resume in a fresh chat here, or start a session locally
with this repo open.

## Then Phase 3 + 4 (not yet built)

- `app/hevy/normalize.py`: Hevy JSON → Data Contract (`source="hevy"`, kg→lb at
  `lb = kg * 2.2046226218` rounded to 0.5, warmup sets excluded); working weight
  = max non-warmup weight per exercise across Push/Pull/New Abs/Upper Mix/Legs.
- `app/hevy/summaries.py`: per-routine / per-workout summaries in the trainer
  log format.
- `/hevy/working-weights`, `/hevy/summary/*` endpoints; unit tests for kg→lb and
  working-weight derivation.
- `app/trainer/service.py` + `/chat`: load `prompts/trainer.md`, compose Module
  B + C context as Data Contract records, call Claude, keep §2 labels.

## Git state

`origin` is `https://github.com/j591fletcher/claude_workout.git`. Your local
`Workout app/` folder and GitHub are both at the same commit (`72d94bb` at time
of writing) — fully synced, no divergence. The old standalone `workout-app/`
subfolder and `workout-app.bundle` (transport artifacts from the handoff) have
been deleted; this folder is now the one and only working copy.
