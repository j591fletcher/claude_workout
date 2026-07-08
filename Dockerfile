FROM python:3.11-slim

WORKDIR /app

# CPU-only torch keeps the image several GB smaller — no GPU on Unraid needed
# for the small sentence-transformers embedder.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY pyproject.toml ./
COPY app ./app
COPY prompts ./prompts
RUN pip install --no-cache-dir .

# Inside the container bind all interfaces; docker-compose publishes the port
# only on 127.0.0.1 / the tailnet IP of the host (CLAUDE.md §1).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
