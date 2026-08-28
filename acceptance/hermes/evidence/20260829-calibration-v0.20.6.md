# Calibration — `runner:hermes` on Hermes v0.20.6 (2026-08-29)

The harness was re-pinned from Hermes v0.17.0 (`v2026.6.19`) to the current **release**
**v0.20.6 (`v2026.8.27`)** — `prerelease=false`, GitHub's own `releases/latest`. A harness that
changes the environment it reproduces must be re-shown to discriminate there; a green run carried
over from the old pin proves nothing about the new one.

## Result on the new pin

```
Hermes Agent v0.20.6 (2026.8.27) · local 5fc308a7
Python: 3.11.16
PASS: loaded 'uacp_guardian' and registered all 19 declared governed tools
```

Artifact: [`20260829-plugin-conformance-v0.20.6.json`](20260829-plugin-conformance-v0.20.6.json).

**Planted fault re-run on the new pin** — restored `class Loaded[T]`:

```
FAIL: Hermes reports 'uacp_guardian' FAILED TO LOAD:
    WARNING hermes_cli.plugins: Failed to load plugin 'uacp_guardian': invalid syntax (loaders.py, line 58)
```

Reverted → PASS. So the harness still catches the defect that motivated it, on the runtime users
actually run today.

## What the bump cost, and why each step is a reproduction rather than a shortcut

v0.20.6's installer is materially heavier than v0.17.0's, and each failure was real:

| Symptom | Cause | Response |
|---|---|---|
| exit 127 | Node **26** (was 22) links `libatomic.so.1`, which `-slim` strips | install `libatomic1` — a base-OS runtime lib any real machine has |
| abort | installer now needs a **C++ compiler** for native modules, and tries `sudo apt install build-essential` itself | install `build-essential` — the installer's own stated requirement; it only fails here because the container user has no sudo |
| `npm install failed`, no output | **node-gyp needs a `python3` on PATH**; the npm step is fatal by design (upstream #85297) and `--skip-browser` does NOT skip it | install `python3` — for node-gyp, not for Hermes |

## The trap that last step set, and the guard that caught it

Adding `python3` broke the reproduction, and the harness said so: the next run reported
**`Python: 3.11.2`** — Debian bookworm's system interpreter — instead of uv's **3.11.16**.
`uv python find 3.11` had happily adopted the system one, so "let Hermes' installer select the
interpreter" silently became "test whatever the base image ships". That run PASSED, and its PASS was
worthless.

Fixed with `UV_PYTHON_PREFERENCE=only-managed`, which forces uv to use only interpreters it
downloaded itself. The two versions differing (3.11.2 vs 3.11.16) is what made the breakage visible
at all, and the Dockerfile now records it as the standing check: **if this run ever reports 3.11.2,
the reproduction has broken and the result is not evidence.**
