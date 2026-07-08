"""Checkpoint 2 helper: fetch ONE real workouts page and ONE routines page and
print their structure, so we can confirm the actual Hevy schema before writing
normalization. Read-only. Run where there's network access to api.hevyapp.com.

    HEVY_API_KEY=... python scripts/hevy_schema_probe.py

Prints field names/types (not a full dump), redacts nothing sensitive beyond
truncating long strings. Safe to paste the output back.
"""

from __future__ import annotations

import os
import sys

import httpx

BASE = "https://api.hevyapp.com"


def shape(value, depth=0):
    pad = "  " * depth
    if isinstance(value, dict):
        lines = []
        for k, v in value.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{pad}{k}:")
                lines.append(shape(v, depth + 1))
            else:
                sample = v if not isinstance(v, str) else v[:40]
                lines.append(f"{pad}{k}: {type(v).__name__} = {sample!r}")
        return "\n".join(lines)
    if isinstance(value, list):
        if not value:
            return f"{pad}[] (empty)"
        return f"{pad}[{len(value)} items] first item:\n" + shape(value[0], depth + 1)
    return f"{pad}{type(value).__name__} = {value!r}"


def main() -> None:
    key = os.environ.get("HEVY_API_KEY")
    if not key:
        sys.exit("Set HEVY_API_KEY in the environment first.")
    client = httpx.Client(base_url=BASE, headers={"api-key": key}, timeout=30.0)
    for path, params in [("/v1/workouts", {"page": 1, "pageSize": 1}),
                         ("/v1/routines", {"page": 1, "pageSize": 1})]:
        print("=" * 70)
        print(f"GET {path}  {params}")
        print("=" * 70)
        resp = client.get(path, params=params)
        print(f"HTTP {resp.status_code}")
        if resp.status_code >= 400:
            print(resp.text[:300])
            continue
        print(shape(resp.json()))
        print()


if __name__ == "__main__":
    main()
