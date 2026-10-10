# obs-smoke

[![Smoke](https://github.com/obs-rust/obs-smoke/actions/workflows/smoke.yml/badge.svg)](https://github.com/obs-rust/obs-smoke/actions/workflows/smoke.yml)

Proves OBS Studio starts on **Windows, macOS and Linux**: each platform installs a
build, launches OBS, waits for `==== Startup complete` in the OBS log and takes a
desktop screenshot while OBS is still running.

**Latest results:** https://obs-rust.github.io/obs-smoke/

[![Latest smoke screenshots: Windows, macOS, Linux](https://raw.githubusercontent.com/obs-rust/obs-smoke/smoke-results/smoke.png)](https://obs-rust.github.io/obs-smoke/)

## Running

Actions → **Smoke** → *Run workflow*, or:

```sh
gh workflow run smoke.yml -R obs-rust/obs-smoke                     # latest green obs-rust/obs-studio master build
gh workflow run smoke.yml -R obs-rust/obs-smoke -f target=32.2.2    # a release tag
gh workflow run smoke.yml -R obs-rust/obs-smoke -f target=latest    # newest release
```

| Input | Default | Meaning |
|---|---|---|
| `target` | `main` | `main` uses the artifacts of the newest successful `push.yaml` run on `obs-rust/obs-studio` `master`; anything else is a release tag (`latest` = newest release). |
| `release_repo` | `obsproject/obs-studio` | Where release tags are looked up. |

Runners: `windows-2025` (x64 zip), `macos-26` (Apple Silicon dmg), `ubuntu-26.04` (deb, under Xvfb).

## Branches

| Branch | Contents |
|---|---|
| `main` | Workflow and scripts. |
| `smoke-results` | Latest run only, force-pushed each run: `results.json`, `smoke.png` (stable montage linked above), `<os>.png`, `logs/<os>.log`. |

A metrics history branch (peak RSS, startup time over time) is planned but not built yet;
`startup_seconds` is already recorded per platform in `results.json`.

## Layout

- `.github/workflows/smoke.yml`: resolve target → per-OS smoke matrix → aggregate, push `smoke-results`, deploy Pages.
- `scripts/run_obs.py`: launch OBS, wait for startup, screenshot, write `result.json`.
- `scripts/aggregate.py`: merge per-OS results into `results.json`.
- `scripts/build_site.py`: render `results.json` into the Pages site.

## Artifact access

Downloading another repository's workflow artifacts may need more than the default
`GITHUB_TOKEN`. If the `main` download fails, add a repository secret `OBS_ARTIFACT_TOKEN`
(fine-grained PAT with *Actions: read* on `obs-rust/obs-studio`); the workflow prefers it when set.
