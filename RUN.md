# Running on Unraid

Single container, bound to the tailnet only (never a public interface).

## First-time setup

```bash
cd /mnt/user/appdata/workout-app   # or wherever this repo lives on the box
```

1. Copy `.env.example` to `.env` and fill in:
   - `HEVY_API_KEY` — from hevy.com/settings?developer
   - `ANTHROPIC_API_KEY` — only needed if `LLM_BACKEND=anthropic`; leave blank for the default local Ollama backend
   - `OLLAMA_BASE_URL` — the GPU host's tailnet address, e.g. `http://100.85.238.56:11500`
   - `BIND_IP` — this Unraid box's own tailnet IP (never `0.0.0.0`), so the API is reachable over Tailscale but not the public internet
2. `pdfs/` is gitignored — copy the program PDFs/xlsx into `./pdfs/` on the box (e.g. `rsync`/`scp` from wherever they live).
3. `docker compose up -d --build`

The container's entrypoint (`docker-entrypoint.sh`) runs ingestion automatically
on first start if `data/chroma` doesn't exist yet — expect the first boot to
take longer while it embeds all program PDFs. Subsequent restarts skip
ingestion. To force a re-ingest (e.g. after adding new PDFs), stop the
container and delete `data/chroma`, then start it again.

## Smoke test

From any machine on the tailnet (replace with the box's tailnet IP):

```bash
curl http://<unraid-tailnet-ip>:8000/health
# {"status":"ok"}

curl -X POST http://<unraid-tailnet-ip>:8000/hevy/summary/routines
# {"routines": ["Push\n...", "Pull\n...", ...]}  — confirms Hevy connectivity

curl -X POST http://<unraid-tailnet-ip>:8000/ask -H "content-type: application/json" \
  -d '{"question":"What are the sets, reps, and RPE for Bench Press?"}'
# grounded answer citing a real program + sources, or "No LLM backend configured"
# if Ollama's unreachable from the box (still proves retrieval works)

curl -X POST http://<unraid-tailnet-ip>:8000/chat -H "content-type: application/json" \
  -d '{"message":"Summarize each of my five routines back to me."}'
# should list Push/Pull/New abs/Upper Mix/Legs with real exercise names

curl http://<unraid-tailnet-ip>:8000/hevy/stats
# dashboard stats: total_workouts, this_week, streak_weeks, recent_prs

curl http://<unraid-tailnet-ip>:8000/hevy/exercises
# every exercise ever logged, most-trained first

curl "http://<unraid-tailnet-ip>:8000/hevy/exercise-history?name=Bench%20Press%20(Barbell)"
# per-session progression series, oldest first — 404 if the name was never logged

curl "http://<unraid-tailnet-ip>:8000/hevy/workouts?limit=5"
# paginated structured workout feed (limit/offset)

curl http://<unraid-tailnet-ip>:8000/hevy/routines/full
# the five tracked routines as structured Exercise rows
```

`docker compose ps` should show the container `healthy` after ~60s (the
healthcheck's `start_period` accounts for a possible first-boot ingest).

## Web UI (mobile PWA)

The container also serves a React frontend at `/` — the API routes above are
unaffected (they're registered before the static mount in `app/main.py`, so
they always win). Open `http://<unraid-tailnet-ip>:8000/` in a browser to
confirm the 5 tabs (Home, History, Progress, Routines, Coach) load and show
real data before bothering with HTTPS/install below.

### HTTPS via Tailscale Serve (required for the PWA install + service worker)

A service worker and a clean "Add to Home Screen" install both require a
secure context — plain `http://<tailnet-ip>:8000` won't offer either on
iPhone. Tailscale Serve gives the box a trusted `https://` URL on the tailnet
without touching `BIND_IP` (Serve proxies from `127.0.0.1`, so the container
keeps binding to localhost only, per CLAUDE.md §1):

```bash
tailscale serve --bg https / http://127.0.0.1:8000
tailscale serve status   # confirm it's proxying and shows the https:// URL
```

This exposes the app at `https://<box-name>.<your-tailnet>.ts.net` — reachable
only over the tailnet, never the public internet. To stop it:
`tailscale serve --https=443 off`.

### Install to an iPhone home screen

1. On the iPhone (joined to the same tailnet), open Safari and go to
   `https://<box-name>.<your-tailnet>.ts.net`.
2. Tap the Share icon, then **Add to Home Screen**.
3. Launch it from the home screen icon — it opens standalone (no Safari
   chrome), and works exactly like the browser tab since it just points at
   the same tailnet URL. No further updates needed on the phone: the service
   worker only caches the app shell, so every tab always fetches live data
   from `/hevy`, `/ask`, and `/chat` on load — nothing goes stale.

## Logs / troubleshooting

```bash
docker compose logs -f workout-app
```

- `HevyError` in logs → check `HEVY_API_KEY` and that the box has outbound
  internet access.
- `/chat` or `/ask` answers say "No LLM backend configured" or an
  "unreachable" message → the Ollama host is off, or `OLLAMA_BASE_URL` is
  wrong, or the GPU host's `OLLAMA_HOST` isn't bound to `0.0.0.0` (see
  HANDOFF.md's Ollama gotchas section).
- Ingestion errors are logged and skipped per-file, never fatal — check logs
  for "Skipping malformed" lines if a program's data looks incomplete.
