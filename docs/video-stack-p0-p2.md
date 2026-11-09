# Video stack P0–P2 — rollout opt-in
Existing video modes, secrets, OAuth, and production workflows remain unchanged.

## Implemented now
- P0: FFmpeg deterministic video normalization and hard cuts; optional 3-second hook; body audio preserved/delayed.
- P0: isolated manual GitHub Actions entrypoint; requires artifact `video-source/input.mp4` from an existing run.
- P1/P2: integration slots below; **not installed or active**.

## Planned adapters (not yet implemented)
- P0: PySceneDetect for scene indexing; Auto-Editor for silence cuts; OpenScreen/Playwright capture; HyperFrames animation renderer.
- P1: Motion Canvas, iArt skills, GL transitions.
- P2: Three.js procedural universe animation.

## Safety
- No API keys, secrets, OAuth routes or existing workflows modified.
- No third-party network media automatically downloaded.
- External clips require rights review; verified news only.
- Runner cost/quotas depend on GitHub plan; self-hosted runner supported.
- Hard cut by default; no artificial white transitions.

## Local example
```bash
python3 scripts/video_stack.py --input source.mp4 --hook hook.mp4 --hook-seconds 3 --output final.mp4
```
Requires FFmpeg and FFprobe on PATH.
