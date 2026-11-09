"""P2: WebGL/Three.js smoke test using local assets and software rendering."""
from __future__ import annotations
import json
import subprocess
from pathlib import Path
from scripts.motion_design import render_threejs_universe
from scripts.video_stack import ffprobe_media

def main():
    dest=Path("qa-three-universe")
    dest.mkdir(exist_ok=True)
    video=dest/"three-universe.mp4"
    render_threejs_universe(video,title="OPEN SOURCE",seconds=.5,size=(320,180),fps=12)
    metadata=ffprobe_media(video)
    if metadata["duration"] < .4 or metadata["duration"] > .75:
        raise AssertionError("Three.js animation has incorrect frame duration")
    if metadata["width"]!=320 or metadata["height"]!=180:
        raise AssertionError("Incorrect WebGL viewport")
    subprocess.run(["ffmpeg","-loglevel","error","-y","-ss","0.25","-i",str(video),
                    "-frames:v","1",str(dest/"three-universe-frame.png")],
                   check=True,timeout=60)
    (dest/"three-universe-qa.json").write_text(
        json.dumps(metadata,indent=2),encoding="utf-8")
    print(json.dumps(metadata))

if __name__=="__main__":
    main()
