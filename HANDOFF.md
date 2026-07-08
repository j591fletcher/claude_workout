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
| 4. Module A trainer wiring (`/chat`) | ✅ done 2026-07-08 | `Wire trainer /chat with local Ollama and grounding guardrails` |
| 5. Deploy polish (Unraid + Tailscale) | ⬜ **do this next** | |

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

## Module A — the LLM runs locally, not on Anthropic

Cost was the deciding factor: `LLM_BACKEND=ollama` in `.env` is the default,
pointing at a gaming PC's GPU over Tailscale (`OLLAMA_BASE_URL`, model
`qwen2.5:14b`, ~9GB at Q4_K_M). `app/llm.py` is a swappable `LLMClient`
interface (same pattern as `app/retriever/embed.py`'s `Embedder`) — both
`Retriever.ask()` and `Trainer.chat()` go through `get_llm_client(settings)`,
so switching back to `LLM_BACKEND=anthropic` later is a one-line `.env` change,
no code change. If the Ollama host is off, both fall back to retrieved-data-only
answers instead of erroring (`LLMUnavailable`).

**Gotchas if you reconnect the GPU host:** Ollama binds to `127.0.0.1` only by
default — needs `OLLAMA_HOST=0.0.0.0:<port>` set on the gaming PC (then restart
the Ollama app) to be reachable over Tailscale, and a Windows Firewall inbound
rule for that port (Tailscale's adapter often lands under the "Public" profile).

## Known limitation: local model grounding reliability

Live-tested 2026-07-08 with real retrieval + real Hevy data. Two real problems
surfaced and got fixed at the code level (not just prompt wording):

1. **Ingestion bug** — `ingest.py` used to hardcode every PDF's `program` field
   to `"Bodybuilding Transformation System"` regardless of which file it came
   from, so prose from actual Nippard PDFs (e.g. Fundamentals Hypertrophy) was
   mislabeled. Fixed: `program_name_from_filename()` derives a real per-file
   name. **Re-run ingest after pulling this** (`data/chroma` was rebuilt
   locally; if you're starting fresh elsewhere, just run ingest once).
2. **qwen2.5:14b still occasionally names "Nippard" or a specific real program
   with zero supporting retrieved excerpt**, even after (a) filtering out
   retrieved chunks with cosine distance > 0.35 (`retrieval_max_distance` in
   `config.py`) and (b) an explicit prompt rule not to trust the user's own
   wording over the excerpt's actual program name. Tightening prompts and
   retrieval narrowed it but didn't eliminate it — a 14B local model just isn't
   fully reliable on this instruction.

   **Mitigation, not a fix:** `flag_ungrounded_programs()` in
   `app/retriever/query.py` runs after every LLM answer and appends a visible
   "⚠️ Grounding check" warning if the answer names a known-ingested program
   that wasn't among its own retrieved sources, or says "Nippard" at all (that
   word is stripped from every program name at ingest time, so its presence in
   an answer is always provably ungrounded). This makes the failure *visible*
   instead of silent — it doesn't make the model stop doing it. Simple,
   well-grounded factual questions (exact sets/reps/RPE lookups) tested clean
   with no false warnings; the risk is concentrated in compound/technique
   questions with weak retrieval matches.

   If this warning shows up often in real use, the next lever is a bigger/better
   local model (VRAM permitting) or switching that specific call path to
   `LLM_BACKEND=anthropic`.

## Known minor inefficiency: duplicate PDFs re-ingested separately

Two pairs of files in `pdfs/` are literal duplicates under near-identical
names (`The Muscle Ladder Get Jacked Using Science...` with/without
`(Z-Library)`; `..._Beginner.pdf` vs `..._Beginner_compressed.pdf`). Both
copies get fully ingested and collapse to the same `program` label, so it's
not a correctness bug — just wasted embeddings/storage. Not fixed; dedupe by
content hash in `ingest.py` if it's worth the effort later.

## Verify Phase 4 locally

```powershell
python -m app.retriever.ingest pdfs\    # only needed if data/chroma doesn't exist yet
uvicorn app.main:app --port 8000
```
Then, in another shell:
```powershell
curl -X POST localhost:8000/chat -H "content-type: application/json" `
  -d '{\"message\":\"Summarize each of my five routines back to me.\"}'
```
Should list Push/Pull/New abs/Upper Mix/Legs with real exercise names pulled
live from Hevy. Progression questions against a real working weight (e.g.
"When should I add weight to Bench Press at 175 lb, 4x6-7?") should apply the
+5lb-upper/+10lb-lower/2-consecutive-sessions rule correctly from
`prompts/trainer.md` — that part is reliable even on the local model.

## Git state

`origin` is `https://github.com/j591fletcher/claude_workout.git`. Your local
`Workout app/` folder and GitHub are both at the same commit (`72d94bb` at time
of writing) — fully synced, no divergence. The old standalone `workout-app/`
subfolder and `workout-app.bundle` (transport artifacts from the handoff) have
been deleted; this folder is now the one and only working copy.
