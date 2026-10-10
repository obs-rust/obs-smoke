#!/usr/bin/env python3
"""Render the results branch into a static site.

Usage: build_site.py RESULTS_DIR SITE_DIR
"""

from __future__ import annotations

import html
import json
import shutil
import sys
from pathlib import Path

LABELS = {"windows": "Windows", "macos": "macOS", "linux": "Linux"}

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OBS Smoke Tests</title>
<style>
:root {{ --bg:#f7f7f8; --fg:#1b1b1f; --muted:#5d5d66; --card:#fff; --line:#e2e2e6;
        --pass:#1a7f37; --fail:#cf222e; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#111214; --fg:#e8e8ea; --muted:#9a9aa3; --card:#1b1c1f; --line:#2c2d31;
          --pass:#3fb950; --fail:#f85149; }}
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--fg);
       font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; }}
main {{ max-width:1200px; margin:0 auto; padding:32px 16px; }}
h1 {{ margin:0 0 4px; font-size:26px; }}
.meta {{ color:var(--muted); margin:0 0 24px; }}
.meta a {{ color:inherit; }}
.badge {{ display:inline-block; padding:2px 10px; border-radius:999px; color:#fff;
         font-weight:600; font-size:13px; }}
.pass {{ background:var(--pass); }} .fail {{ background:var(--fail); }}
.grid {{ display:grid; gap:20px; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:10px; overflow:hidden; }}
.card img {{ display:block; width:100%; height:auto; border-bottom:1px solid var(--line); }}
.noimg {{ padding:60px 16px; text-align:center; color:var(--muted); border-bottom:1px solid var(--line); }}
.body {{ padding:14px 16px; }}
.body h2 {{ margin:0 0 8px; font-size:18px; display:flex; justify-content:space-between; align-items:center; }}
dl {{ display:grid; grid-template-columns:max-content 1fr; gap:2px 12px; margin:0; font-size:14px; }}
dt {{ color:var(--muted); }} dd {{ margin:0; overflow-wrap:anywhere; }}
.err {{ color:var(--fail); font-size:14px; margin-top:8px; overflow-wrap:anywhere; }}
footer {{ margin-top:32px; color:var(--muted); font-size:13px; }}
footer a {{ color:inherit; }}
</style>
</head>
<body>
<main>
<h1>OBS Rust smoke tests <span class="badge {status}">{status_text}</span></h1>
<p class="meta">Target <strong>{target}</strong> · {source} · run <a href="{run_url}">#{run_id}</a> · {generated}</p>
<div class="grid">
{cards}
</div>
<footer>Raw data: <a href="results.json">results.json</a> · Each platform builds obs-rust/obs-studio with
ENABLE_RUST_LIBOBS=ON, checks that Rust code is linked into libobs, launches OBS, waits for
"Startup complete" in the OBS log, then screenshots the desktop while OBS is still running.</footer>
</main>
</body>
</html>
"""

CARD = """<section class="card">
{image}
<div class="body">
<h2>{label} <span class="badge {status}">{status_text}</span></h2>
<dl>
<dt>OBS version</dt><dd>{version}</dd>
<dt>Rust libobs</dt><dd>{rust}</dd>
<dt>Startup</dt><dd>{startup}</dd>
<dt>Runner</dt><dd>{runner}</dd>
<dt>Log</dt><dd>{log}</dd>
</dl>
{error}
</div>
</section>"""


def esc(v) -> str:
    return html.escape(str(v)) if v not in (None, "") else "—"


def main() -> int:
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".git"))
    data = json.loads((src / "results.json").read_text())

    cards = []
    for p in data["platforms"]:
        shot = p.get("screenshot")
        image = (
            f'<a href="{esc(shot)}"><img src="{esc(shot)}" alt="OBS on {LABELS[p["os"]]}" loading="lazy"></a>'
            if shot
            else '<div class="noimg">No screenshot</div>'
        )
        secs = p.get("startup_seconds")
        cards.append(
            CARD.format(
                image=image,
                label=LABELS[p["os"]],
                status=p["status"],
                status_text=p["status"].upper(),
                version=esc(p.get("obs_version")),
                rust={True: "yes", False: "NO"}.get(p.get("rust_libobs"), "—"),
                startup=f"{secs:.1f} s" if isinstance(secs, (int, float)) else "—",
                runner=esc(" ".join(filter(None, [p.get("runner_image"), p.get("arch")]))),
                log=f'<a href="{esc(p["log"])}">{esc(p["log"])}</a>' if p.get("log") else "—",
                error=f'<p class="err">{esc(p["error"])}</p>' if p.get("error") else "",
            )
        )

    t = data["target"]
    source = (
            f'<a href="{esc(t["source_url"])}">{esc(t["repo"])}@{esc(t["ref"])} '
            f'{esc((t.get("sha") or "")[:10])}</a>'
    )
    (dst / "index.html").write_text(
        PAGE.format(
            status=data["status"],
            status_text=data["status"].upper(),
            target=esc(t.get("requested")),
            source=source,
            run_url=esc(data["run"]["url"]),
            run_id=esc(data["run"]["id"]),
            generated=esc(data["generated_at"]),
            cards="\n".join(cards),
        )
    )
    (dst / ".nojekyll").write_text("")
    return 0


if __name__ == "__main__":
    sys.exit(main())
