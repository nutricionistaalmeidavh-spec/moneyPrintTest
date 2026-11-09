"""E2E media smoke for the isolated open-source P0-P2 editor."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from scripts.video_stack import render_stack, ffprobe_media


def run(argv):
    subprocess.run(argv, check=True, timeout=180, capture_output=True)


def synthetic_clip(target: Path, *, seconds: float, color: str, hz: int) -> None:
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
        "-f", "lavfi", "-i", f"color=c={color}:s=320x180:r=30:d={seconds}",
        "-f", "lavfi", "-i", f"sine=frequency={hz}:sample_rate=48000:duration={seconds}",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "96k", "-shortest", str(target),
    ])


def smoke(output: Path, transition: str) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="moneyprint-qa-") as folder:
        workspace = Path(folder)
        assets = workspace / "assets"
        assets.mkdir()
        hook = assets / "hook.mp4"
        body = workspace / "body.mp4"
        synthetic_clip(hook, seconds=0.8, color="red", hz=440)
        synthetic_clip(body, seconds=1.6, color="blue", hz=660)
        output_video = output / f"qa-{transition}.mp4"
        report = render_stack(
            body, output_video, assets=assets,
            options={
                "hook_asset": "assets/hook.mp4", "hook_seconds": 0.6,
                "universe_seconds": 0.75, "universe_title": "OPEN SOURCE",
                "aspect": "1:1", "transition": transition,
            },
        )
        streams = ffprobe_media(output_video)
        expected = 0.6 + 0.75 + streams["duration"] - report["duration_seconds"]
        # Direct expectation based on the actual resulting video, not on a
        # video stream timestamp inferred from the audio.
        planned = 0.6 + 0.75 + ffprobe_media(body)["duration"]
        if transition != "cut":
            planned -= 2 * 0.24
        if abs(streams["duration"] - planned) > 0.24:
            raise AssertionError(f"Duration drift: {streams['duration']} vs {planned}")
        if not streams["has_audio"] or not report["audio_preserved"]:
            raise AssertionError("Body audio was lost")
        if report["transition"] != ("hard_cut" if transition == "cut" else transition):
            raise AssertionError("Selected transition was not rendered")
        for label, at in (("hook", .15), ("opening", .85), ("body", max(.2, streams["duration"]-.35))):
            run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                 "-ss", str(at), "-i", str(output_video), "-frames:v", "1",
                 str(output / f"{transition}-{label}.png")])
        report["qa"] = {"planned_seconds": round(planned, 3),
                        "has_audio": streams["has_audio"], "frames_checked": 3}
        (output / f"qa-{transition}.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="qa-video-stack")
    parser.add_argument("--transition", choices=["cut", "fade"], default="cut")
    args = parser.parse_args()
    report = smoke(Path(args.output), args.transition)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
