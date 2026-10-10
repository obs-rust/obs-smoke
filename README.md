# obs-smoke

[![Smoke](https://github.com/obs-rust/obs-smoke/actions/workflows/smoke.yml/badge.svg)](https://github.com/obs-rust/obs-smoke/actions/workflows/smoke.yml)

Proves the **Rust build of OBS** ([obs-rust/obs-studio](https://github.com/obs-rust/obs-studio)) starts on
**Windows, macOS and Linux**. Each platform builds the fork with `ENABLE_RUST_LIBOBS=ON`, checks that Rust
code is linked into libobs, installs the package, launches OBS, checks that it identifies itself as
`OBS-Studio-Rust <version>`, waits for `==== Startup complete` in the OBS
log and takes a desktop screenshot while OBS is still running. Upstream OBS builds are never used.

**Latest results:** https://obs-rust.github.io/obs-smoke/

[![Latest smoke screenshots: Windows, macOS, Linux](https://raw.githubusercontent.com/obs-rust/obs-smoke/smoke-results/smoke.png)](https://obs-rust.github.io/obs-smoke/)

## Running

Actions → **Smoke** → *Run workflow*, or:

```sh
gh workflow run smoke.yml -R obs-rust/obs-smoke                     # obs-rust/obs-studio master
gh workflow run smoke.yml -R obs-rust/obs-smoke -f target=32.2.2    # a release tag of the fork
gh workflow run smoke.yml -R obs-rust/obs-smoke -f target=<branch-or-sha>
```

| Input | Default | Meaning |
|---|---|---|
| `target` | `main` | Ref of `obs-rust/obs-studio` to build: `main` (= `master`), a tag, a branch or a commit SHA. |

Builds run on the fork's CI images (`windows-2025-vs2026` x64, `macos-26` arm64, `ubuntu-26.04` x86_64)
with the fork's own `build-obs`/`package-obs` actions; a cold build takes roughly 30–60 minutes.
Smoke runs on `windows-2025`, `macos-26` and `ubuntu-26.04` (under Xvfb).

## Branches

| Branch | Contents |
|---|---|
| `main` | Workflow and scripts. |
| `smoke-results` | Latest run only, force-pushed each run: `results.json`, `smoke.png` (stable montage linked above), `<os>.png`, `logs/<os>.log`. |

A metrics history branch (peak RSS, startup time over time) is planned but not built yet;
`startup_seconds` is already recorded per platform in `results.json`.

## Layout

- `.github/workflows/smoke.yml`: resolve target → build the Rust fork per OS → per-OS smoke matrix → aggregate, push `smoke-results`, deploy Pages.
- `scripts/run_obs.py`: launch OBS, wait for startup, screenshot, write `result.json`.
- `scripts/aggregate.py`: merge per-OS results into `results.json`.
- `scripts/build_site.py`: render `results.json` into the Pages site.
