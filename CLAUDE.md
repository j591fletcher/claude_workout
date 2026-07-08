# Workout App — Constitution

These rules apply to every module and every session. The full master build prompt
(phases, checkpoints, module specs) lives at `docs/BUILD_PROMPT.md` — reference it
for scope and build order; the rules below are restated here because they are
load-bearing everywhere.

## 1. Security & secrets

- The **Anthropic API key** and the **Hevy API key** come from env vars / Docker
  secrets (`.env`, never committed). Never hardcode, never commit, never send
  either to any client.
- Everything runs as Docker containers on an **Unraid** server, reached over
  **Tailscale**. Bind to localhost/tailnet only — never expose to the public
  internet. No multi-user support, no auth/accounts, no sharing/export features.

## 2. Grounding & labeling

Retrieve from the Nippard PDFs as the primary source. Reasoning beyond them with
general coaching knowledge is allowed, but every answer MUST clearly label which
is which: **"from your Nippard program"** vs. **"general coaching."**
Never silently invent program specifics or attribute made-up advice to Nippard.
If a program detail isn't in the retrieved chunks, say so.

## 3. Shared Data Contract

Exercises pass between modules as structured data, never loose prose. The single
source of truth is the pydantic model in `app/contract.py`:

```
{ "exercise": str, "sets": int, "reps": str,   # e.g. "8-10"
  "rpe": str, "rest": str, "weight": float|null,
  "unit": "lb", "source": "nippard"|"hevy"|"coaching", "notes": str|null }
```

- Retriever (Module B) emits `source: "nippard"`.
- Hevy layer (Module C) emits `source: "hevy"` (weights converted kg → lb).
- Trainer (Module A) tags its own suggestions `source: "coaching"`.

Working weights derived from Hevy are max logged weights, **not 1RMs** — never
compute percentages from them.
