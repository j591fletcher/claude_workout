# MASTER BUILD PROMPT — Personal Workout App

**How to use this:** Paste into Claude Code in **plan mode**, with the lead agent
running on **Claude Fable 5**. Do NOT let it start writing code from this prompt.
Its first job is to produce a phased plan and stop for my approval.

---

## 0. ORCHESTRATION INSTRUCTIONS (read first — these govern HOW you build)

- **Plan first.** Produce a phased build plan from this document and STOP. Wait for
  my explicit approval before writing any code. Do not one-shot the whole app.
- **Phased execution with hard checkpoints.** Build in the order in Section 5.
  At the two checkpoints marked **[STOP FOR SIGN-OFF]**, halt and show me the result
  before building anything on top of it. These are the two riskiest seams (PDF table
  extraction and the real Hevy response schema) and I will not approve blind.
- **Small first milestone.** The first shippable target is narrow: the retriever
  answers ONE grounded question about ONE program correctly. Prove that before
  expanding. Do not let the plan balloon.
- **Scope fence.** This is a single-user app for me. Do NOT build multi-user
  support, authentication/accounts, sharing, or export features. Keep it lean.
- **Subagents — use sparingly and only where they earn their place:**
  - Use the built-in **Explore** agent (and plan mode's own research) to map the
    Hevy API docs and inspect sample PDFs — keep that noisy output out of the main context.
  - During PLANNING ONLY, you may spawn **two parallel research subagents**:
    one to study the Hevy API (https://api.hevyapp.com/docs/) and one to determine a
    table-preserving PDF extraction approach. Route these narrow research/review
    agents to a **cheaper/faster model (Haiku-class)** to control cost. Have each
    return a short structured summary, not raw dumps.
  - Use one **review/grounding-audit pass** before each phase is marked done.
  - Do NOT build an elaborate multi-agent pipeline, hooks, or custom specialist
    agents beyond the above. Keep the main agent holistically in charge.
- **CLAUDE.md as the constitution.** Create a root `CLAUDE.md` capturing the two
  Global Rules (Section 1) and the Shared Data Contract (Section 1.3) so every
  agent and every future session stays aligned. Reference it, don't restate it.
- **After each stage, tell me exactly how to test it before moving on.**
- **Version control.** Initialize git at the very start, and BEFORE the first commit
  create a `.gitignore` that excludes secrets/`.env`, the Nippard PDFs, and the Chroma
  vector store (never commit keys or large binaries). Commit locally after each phase
  in Section 5 completes and after I approve each checkpoint — don't push to a remote
  unless I ask. Write commit messages I can skim and instantly get the gist of:
  a short, plain-English imperative subject line (~50 chars, no jargon), one optional
  line of context only if the change isn't self-explanatory. Good examples:
  "Scaffold repo, Docker, and secrets wiring", "Add PDF ingestion with table-preserving
  extraction", "Add /ask endpoint returning answers with sources", "Add Hevy client and
  working-weight derivation". Avoid vague messages like "update", "wip", or "fix stuff".

---

## 1. GLOBAL RULES (apply to every module — put these in CLAUDE.md)

### 1.1 Security & secrets
- The **Anthropic API key** and the **Hevy API key** come from env vars / Docker
  secrets. Never hardcode, never commit, never send either to any client.
- Everything runs as Docker containers on my **Unraid** server, reached over
  **Tailscale**. Bind to localhost/tailnet only — never expose to the public internet.

### 1.2 Grounding & labeling
Retrieve from the Nippard PDFs as the primary source. You MAY reason beyond them
using general coaching knowledge, but you MUST clearly label which is which in
every answer: **"from your Nippard program"** vs. **"general coaching."**
Never silently invent program specifics or attribute made-up advice to Nippard.
If asked for a program detail that isn't in the retrieved chunks, say so.

### 1.3 Shared Data Contract (all three modules speak this shape)
Exercises are passed between modules as structured data, never loose prose:
```
{ "exercise": str, "sets": int, "reps": str,   # e.g. "8-10"
  "rpe": str, "rest": str, "weight": float|null,
  "unit": "lb", "source": "nippard"|"hevy"|"coaching", "notes": str|null }
```
The retriever, the Hevy layer, and the trainer all produce/consume this shape so
progression math and comparisons work cleanly.

---

## 2. MODULE A — TRAINER BEHAVIOR (this is the APP's RUNTIME SYSTEM PROMPT)

> **Builder note:** The block below is the system prompt for the app's trainer
> persona *at runtime*. Store it as a config/prompt file (e.g. `prompts/trainer.md`)
> and load it when calling the Anthropic API. It is NOT an instruction for you, the
> builder — do not adopt this persona while building.

```
-------------------------------------
IDENTITY
-------------------------------------
You are a personal trainer AI built specifically for me. You are direct,
knowledgeable, and evidence-based. No fluff — talk like a coach who actually
trains. Ground your programming in my Jeff Nippard programs first; you may also
draw on established exercise-science principles, but always label which is which
("from your Nippard program" vs. "general coaching"). Adapt your tone to me over time.
-------------------------------------
CURRENT WORKING WEIGHTS
-------------------------------------
My current working weights are the actual weights I lift in sessions. The app
supplies them to you, derived from my Hevy logs as the max weight of each
exercise. These are NOT one-rep maxes. Do not calculate percentages from them.
Use them as the starting point and apply RPE-based progression only.

My routines in Hevy are: Push, Pull, New Abs, Upper Mix, and Legs (quads,
hamstrings, glutes, calves). When I ask, verify your understanding by summarizing
each routine's exercises back to me before you program from them.
-------------------------------------
LIFT LOG
-------------------------------------
Each logged session looks like this:
[DATE] — Session Name
Exercise | Sets x Reps | Weight | RPE | Notes
Session notes: [how it felt, energy, anything notable]

Old entries are never deleted — the log is the source of truth for working weights
and progress tracking. After a few sessions, the log takes over from the initial
working weights as the primary reference.
-------------------------------------
WORKOUT PROGRAMMING RULES
-------------------------------------
- Use RPE-based loading (RPE 7-8 for hypertrophy work, 8-9 for strength work)
- Never calculate working weights from percentages — always use the logged
  working weights as the baseline
- Progressive overload: add load once I hit the top of a rep range at target
  RPE for 2 consecutive sessions:
    - Upper-body compounds: +5 lb
    - Lower-body compounds: +10 lb
    - Accessories: add reps before adding weight
- Suggest a deload every 4-6 weeks, or sooner if I flag fatigue or stalling
- Prioritize compound movements; use accessories to address weak points
- Treat Week 1 of any new program as a calibration week — flag anything
  that needs adjusting before Week 2
- Base each new session on my most recent log entries
```

---

## 3. MODULE B — PDF RETRIEVER (RAG backend)

Build the retrieval layer that grounds answers in the Nippard PDFs.

**Stack (opinionated — override only with a stated reason):**
- Python 3.11+, FastAPI + Uvicorn.
- PDF extraction with **pdfplumber**, **preserving table structure** (sets / reps /
  RPE / rest columns). Flattening tables into plain text is unacceptable.
- **Structure-aware chunking:** program → phase/mesocycle → day → exercise where the
  PDF allows. Attach metadata to every chunk:
  `{program_name, phase, week, day, exercise, chunk_type}`.
- **Embeddings:** a local `sentence-transformers` model, behind a **swappable
  interface** so a hosted embedder can replace it later without a rewrite.
- **Vector store:** Chroma, persisted to a Docker volume.
- **LLM:** Anthropic Messages API; model name in config.

**Behavior:**
- Ingestion CLI: folder of PDFs → extract → chunk+metadata → embed → load into Chroma.
  Idempotent, re-runnable, logs what it did, skips a malformed PDF and continues.
- Retrieval API: `POST /ask {question, optional metadata filters}` → embed query →
  retrieve top-k (with metadata filtering) → build a grounded prompt → call Claude →
  return the answer **plus which sources it used** (program/phase/day).
- **Structured output:** the retriever must be able to return exercise data in the
  Shared Data Contract shape (Section 1.3), tagged `source: "nippard"`, not just prose.
- Enforce the grounding+labeling rule (Section 1.2).
- `GET /health` endpoint.
- Expose the retriever as a **clean importable module** so Modules A and C consume it
  without refactoring.

**[STOP FOR SIGN-OFF] — Checkpoint 1:** Before building the full pipeline, inspect
ONE sample PDF I point you to and show me: your extraction approach, the proposed
chunk schema, the metadata fields, and a real example of an extracted set/rep/RPE
table proving the columns survived. Wait for my approval.

---

## 4. MODULE C — HEVY INTEGRATION (live data / progress tracking)

Tracking is Hevy, via its API — not a database you invent.

- Read from the Hevy API (docs: https://api.hevyapp.com/docs/) using my key (a secret).
  Pull routines, templates, and workouts. **Read-only** — I log in Hevy normally; the
  app only pulls. Do not write to Hevy unless I explicitly ask later.
- Derive **current working weights** = the **max weight per exercise** from my logged
  data across these routines: Push, Pull, New Abs, Upper Mix, Legs. These are NOT 1RMs;
  do not compute percentages from them (per the trainer rules).
- Normalize Hevy data into the Shared Data Contract shape, tagged `source: "hevy"`.
- Produce a **per-workout summary** I can verify, so I can confirm the app understood
  my routines correctly (the trainer prompt requires this verification step).
- Sibling module to the retriever; both feed the trainer layer.

**[STOP FOR SIGN-OFF] — Checkpoint 2:** Before building on the Hevy data, fetch ONE
real response from the Hevy API and show me the ACTUAL response schema. Do not assume
the shape — confirm it against a live call, then map it to the Data Contract.

---

## 5. BUILD ORDER

1. Repo scaffold + `CLAUDE.md` (Global Rules + Data Contract) + secrets wiring +
   Docker/compose sized for Unraid, Tailscale-bound.
2. **Checkpoint 1** (PDF extraction proof) → then Module B ingestion → retrieval API.
   **First milestone:** one grounded, correctly-sourced answer about one program.
3. **Checkpoint 2** (real Hevy schema) → then Module C read + normalization + summaries.
4. Wire Module A (trainer prompt) to consume B + C via the Data Contract.
5. Only after all of the above is working: the phone front-end (out of scope here —
   plan for a self-hosted PWA reached over Tailscale, but do not build it yet).

**Quality bar:** typed functions, config centralized, meaningful logging, graceful
handling of malformed PDFs and Hevy API errors.
