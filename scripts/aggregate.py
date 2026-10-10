#!/usr/bin/env python3
"""Merge per-platform smoke results into one results.json.

Usage: aggregate.py IN_DIR OUT_DIR

IN_DIR holds one sub-directory per platform (downloaded artifacts), each with
result.json, <os>.png and <os>.log. Run metadata comes from SMOKE_* and
GITHUB_* environment variables. OUT_DIR receives results.json plus every
screenshot and log, flattened, which is the layout of the results branch.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

PLATFORMS = ["windows", "macos", "linux"]


def main() -> int:
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    dst.mkdir(parents=True, exist_ok=True)
    (dst / "logs").mkdir(exist_ok=True)

    found: dict[str, dict] = {}
    for rj in src.glob("*/result.json"):
        r = json.loads(rj.read_text())
        info = rj.parent / "build-info.json"
        if info.exists():
            r.update(json.loads(info.read_text()))
        for name in (r.get("screenshot"), r.get("log")):
            if name and (rj.parent / name).exists():
                sub = "logs" if name.endswith(".log") else ""
                shutil.copy(rj.parent / name, dst / sub / name)
        if r.get("log"):
            r["log"] = f"logs/{r['log']}"
        found[r["os"]] = r

    for r in found.values():
        if r.get("status") == "pass" and r.get("rust_libobs") is not True:
            r["status"] = "fail"
            r["error"] = "OBS started, but the build has no Rust code in libobs"
        elif r.get("status") == "pass" and r.get("product") != "OBS-Studio-Rust":
            r["status"] = "fail"
            r["error"] = f"Rust build identifies itself as {r.get('product')!r}, not 'OBS-Studio-Rust'"
    platforms = [
        found.get(p, {"os": p, "status": "fail", "error": "smoke job produced no result"}) for p in PLATFORMS
    ]
    env = os.environ
    server = env.get("GITHUB_SERVER_URL", "https://github.com")
    results = {
        "schema": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rust_libobs": all(p.get("rust_libobs") is True for p in platforms),
        "status": "pass" if all(p["status"] == "pass" for p in platforms) else "fail",
        "target": {
            "requested": env.get("SMOKE_TARGET", ""),
            "kind": env.get("SMOKE_KIND", ""),
            "repo": env.get("SMOKE_REPO", ""),
            "ref": env.get("SMOKE_REF", ""),
            "sha": env.get("SMOKE_SHA", ""),
            "source_url": env.get("SMOKE_SOURCE_URL", ""),
        },
        "run": {
            "id": env.get("GITHUB_RUN_ID", ""),
            "url": f"{server}/{env.get('GITHUB_REPOSITORY', '')}/actions/runs/{env.get('GITHUB_RUN_ID', '')}",
            "commit": env.get("GITHUB_SHA", ""),
            "trigger": env.get("GITHUB_EVENT_NAME", ""),
        },
        "platforms": platforms,
    }
    (dst / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
