# Running the logo workflow on your laptop

The logo design workflow lives at `.claude/workflows/kubrique-orbital-mark.js`.
Claude Code picks it up automatically when started from the repo root.

## One-time setup (Windows)

1. Pull this branch: `git fetch origin brand/logo && git checkout brand/logo`
2. Make sure Google Chrome or Microsoft Edge is installed (used headlessly to render review images).
3. Make sure Python 3 is installed (`python --version`). No extra packages needed.
4. Optional: put inspiration photos in `brand/reference/` (any .jpg/.png). The workflow runs fine without them.

## Run it

Open Claude Code in the repo root and say:

> use a workflow: run the `kubrique-orbital-mark` workflow

(or turn on ultracode and ask for the logo).

Output lands in `brand/work/orbital/`:

- `A/`, `B/`, `C/`, `D/`: the four candidate constructions with review renders
- `final/mark-static.svg`, `final/mark-animated.svg`, `final/frames.png`

The refiner also overwrites `brand/kubrique-logo-static.svg` and `brand/kubrique-logo.svg` with the finished mark.

## Options

Pass args to change folders, for example `{ "refsDir": "brand/reference", "workDir": "brand/work/orbital" }`.

## If it stops part way

Ask Claude to resume with the run ID it printed; completed agents return cached results.
