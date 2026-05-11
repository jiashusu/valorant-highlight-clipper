# Valorant Highlight Clipper

A local macOS web app that scans VALORANT recordings and exports highlight clips from detected kill-feed events.

> Important: the actual clipper runs locally on your Mac. It needs access to local video files, `ffmpeg`, and long-running CPU work. Vercel is used only for the static project page, not for processing gameplay videos.

## Features

- Local browser UI at `http://127.0.0.1:8787`
- Drag a video or folder into the page
- macOS file/folder picker buttons
- Automatic VALORANT kill-feed detection using the included model weights
- Clip export with estimated kill count per clip
- Strict mode to reduce teammate-kill false positives
- Control launcher with Start, Stop, Restart, and Status options

## Requirements

- macOS
- Python 3.11+
- `ffmpeg` and `ffprobe`

Install ffmpeg with Homebrew:

```bash
brew install ffmpeg
```

## Quick Start

```bash
git clone https://github.com/jiashusu/valorant-highlight-clipper.git
cd valorant-highlight-clipper
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
PYTHONPATH=src python -m uvicorn valorant_clipper.web_app:app --host 127.0.0.1 --port 8787
```

Open:

```text
http://127.0.0.1:8787
```

## macOS Launchers

Run the control launcher:

```bash
bin/valorant_clipper_control.command
```

It offers:

- Start
- Stop
- Restart
- Current status

You can also use command-line actions:

```bash
bin/valorant_clipper_control.command status
bin/valorant_clipper_control.command start
bin/valorant_clipper_control.command stop
bin/valorant_clipper_control.command restart
```

Optional: compile the AppleScript launchers into `.app` bundles:

```bash
osacompile -o "bin/Valorant Clipper Control.app" "bin/Valorant Clipper Control.applescript"
osacompile -o "bin/Valorant Highlight Clipper.app" "bin/Valorant Highlight Clipper.applescript"
```

## Default Paths

The app defaults to:

```text
~/Movies/VALORANT_CLIPS
```

Override it before starting:

```bash
export VALORANT_CLIPS_DIR="/path/to/your/clips"
bin/valorant_clipper_control.command start
```

Exports are written to:

```text
outputs/valorant_highlights
```

## Tuning Detection

The app includes a strict mode for reducing teammate-kill false positives.

Recommended starting values:

- Confidence: `0.8`
- Strict teammate filtering: on
- Minimum event seconds: `0.45`

If teammate kills are still included, raise minimum event seconds to `0.55` or `0.65`.

If your own kills are missed, lower it to `0.35` or turn strict filtering off.

## Why Vercel Cannot Run the Clipper

This app processes large local recordings with `ffmpeg`. Typical VALORANT files can be several GB, and processing can take minutes. Vercel serverless deployments cannot access files on your Mac, cannot open macOS file pickers, and are not designed for long local video-processing jobs.

The repository includes a Vercel-compatible static page in `public/` so the project can still have a public Vercel URL.

## Project Structure

```text
assets/valorant_clipper/    model weights and mask
bin/                        local launch/control scripts
public/                     Vercel static page
src/valorant_clipper/       FastAPI app and clipping engine
static/valorant_clipper/    local web UI
tests/                      lightweight core tests
```

## License

Personal project. Check upstream model/assets licensing before redistributing beyond your own account.

