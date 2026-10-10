#!/usr/bin/env python3
"""Launch an installed OBS Studio, wait for startup, take a screenshot.

Usage: run_obs.py --os {linux,macos,windows} --exe PATH --out DIR [--timeout S]

Writes DIR/result.json, DIR/<os>.png and DIR/<os>.log. Exits 0 even when the
smoke check fails so the publish job can still record the failure; the
"status" field in result.json is the verdict.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

STARTUP_MARKER = "==== Startup complete"
VERSION_RE = re.compile(r"OBS (\d+\.\d+\.\d+\S*) \(")


def config_dir(os_name: str) -> Path:
    home = Path.home()
    if os_name == "windows":
        return Path(os.environ["APPDATA"]) / "obs-studio"
    if os_name == "macos":
        return home / "Library" / "Application Support" / "obs-studio"
    return home / ".config" / "obs-studio"


def seed_config(cfg: Path) -> None:
    """Skip the first-run auto-configuration wizard and update checks."""
    cfg.mkdir(parents=True, exist_ok=True)
    general = "[General]\nFirstRun=true\nEnableAutoUpdates=false\nInfoIncrement=-1\n"
    for name in ("global.ini", "user.ini"):
        (cfg / name).write_text(general)


def newest_log(cfg: Path) -> Path | None:
    logs = sorted(glob.glob(str(cfg / "logs" / "*.txt")), key=os.path.getmtime)
    return Path(logs[-1]) if logs else None


def screenshot(os_name: str, dest: Path) -> str | None:
    try:
        if os_name == "linux":
            subprocess.run(["import", "-window", "root", str(dest)], check=True, timeout=60)
        elif os_name == "macos":
            subprocess.run(["screencapture", "-x", str(dest)], check=True, timeout=60)
        else:
            ps = (
                "Add-Type -AssemblyName System.Windows.Forms,System.Drawing;"
                "$b=[System.Windows.Forms.SystemInformation]::VirtualScreen;"
                "$bmp=New-Object System.Drawing.Bitmap $b.Width,$b.Height;"
                "$g=[System.Drawing.Graphics]::FromImage($bmp);"
                "$g.CopyFromScreen($b.Left,$b.Top,0,0,$bmp.Size);"
                f"$bmp.Save('{dest}',[System.Drawing.Imaging.ImageFormat]::Png)"
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, timeout=60)
    except Exception as exc:  # noqa: BLE001 - recorded in result.json
        return f"screenshot failed: {exc}"
    return None if dest.exists() else "screenshot produced no file"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--os", required=True, choices=["linux", "macos", "windows"])
    ap.add_argument("--exe", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--settle", type=float, default=10.0, help="seconds to wait after startup before the screenshot")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    exe = Path(args.exe).resolve()
    cfg = config_dir(args.os)
    seed_config(cfg)

    result: dict = {
        "os": args.os,
        "arch": platform.machine(),
        "runner": os.environ.get("RUNNER_NAME", ""),
        "runner_image": os.environ.get("ImageOS", ""),
        "status": "fail",
        "startup_complete": False,
        "startup_seconds": None,
        "alive_at_screenshot": False,
        "obs_version": None,
        "screenshot": None,
        "log": None,
        "error": None,
    }

    cmd = [str(exe), "--disable-updater", "--disable-shutdown-check", "--disable-missing-files-check"]
    start = time.monotonic()
    proc = subprocess.Popen(cmd, cwd=str(exe.parent), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    log_path = None
    while time.monotonic() - start < args.timeout:
        if proc.poll() is not None:
            result["error"] = f"OBS exited early with code {proc.returncode}"
            break
        log_path = newest_log(cfg)
        if log_path and STARTUP_MARKER in log_path.read_text(errors="replace"):
            result["startup_complete"] = True
            result["startup_seconds"] = round(time.monotonic() - start, 2)
            break
        time.sleep(0.5)
    else:
        result["error"] = f"no '{STARTUP_MARKER}' in log after {args.timeout:.0f}s"

    if proc.poll() is None:
        time.sleep(args.settle)
    result["alive_at_screenshot"] = proc.poll() is None

    shot = out / f"{args.os}.png"
    shot_err = screenshot(args.os, shot)
    if shot_err:
        result["error"] = "; ".join(filter(None, [result["error"], shot_err]))
    else:
        result["screenshot"] = shot.name

    if proc.poll() is None:
        proc.kill()
    stdout = proc.communicate(timeout=30)[0].decode(errors="replace")
    (out / f"{args.os}-stdout.txt").write_text(stdout)

    log_path = newest_log(cfg)
    if log_path:
        text = log_path.read_text(errors="replace")
        shutil.copy(log_path, out / f"{args.os}.log")
        result["log"] = f"{args.os}.log"
        m = VERSION_RE.search(text)
        if m:
            result["obs_version"] = m.group(1)

    if result["startup_complete"] and result["alive_at_screenshot"] and result["screenshot"]:
        result["status"] = "pass"
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
