"""Audit/recover actual Kaggle kernel output media, never fabricate a video."""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

VIDEOS = {".mp4", ".mov", ".mkv", ".webm"}
OUTPUTS = VIDEOS | {".png", ".jpg", ".jpeg", ".wav", ".srt", ".json", ".txt"}


def inspect_video(path: Path) -> dict | None:
    try:
        process=subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=codec_name,width,height,nb_frames:format=duration",
             "-of", "json", str(path)], check=True, capture_output=True,
            text=True, timeout=20,
        )
        probe=json.loads(process.stdout)
        tracks=probe.get("streams",[])
        if not tracks:
            return None
        track=tracks[0]
        duration=float(probe.get("format",{}).get("duration") or 0)
        if duration <= 0.0 or track.get("width",0)<=0 or track.get("height",0)<=0:
            return None
        return {"duration_seconds":round(duration,3), "width":track["width"],
                "height":track["height"],"codec":track.get("codec_name","unknown")}
    except (OSError,ValueError,subprocess.CalledProcessError,subprocess.TimeoutExpired):
        return None


def recover_mp4(file: Path) -> Path | None:
    """Try stream remux, retaining original; cannot recover a missing MP4 moov."""
    if file.suffix.lower() not in VIDEOS or not file.is_file():
        return None
    target=file.with_name(file.stem+"-remux.mp4")
    if target.exists():
        return target if inspect_video(target) else None
    try:
        subprocess.run(
            ["ffmpeg", "-hide_banner","-loglevel","error","-y","-fflags","+genpts",
             "-err_detect","ignore_err","-i",str(file),
             "-map","0:v:0","-map","0:a?","-c","copy","-movflags","+faststart",
             str(target)],
            check=True,capture_output=True,timeout=70,
        )
        if inspect_video(target):
            return target
    except (OSError,subprocess.CalledProcessError,subprocess.TimeoutExpired):
        pass
    target.unlink(missing_ok=True)
    return None


def collect_media(folder: Path) -> dict:
    if not folder.exists():
        return {"status":"no_video_available", "files":[], "playable_videos":[]}
    all_files=[]
    playable=[]
    broken_count=0
    for path in sorted(folder.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in OUTPUTS:
            continue
        # Paths are relative, never expose credentials or hidden parent paths.
        record={
            "name":str(path.relative_to(folder)),
            "bytes":path.stat().st_size,
            "sha256":hashlib.sha256(path.read_bytes()).hexdigest() if path.stat().st_size<250_000_000 else "not_hashed_large_file",
        }
        if path.suffix.lower() in VIDEOS:
            qa=inspect_video(path)
            if qa is None:
                broken_count+=1
                target=recover_mp4(path)
                if target:
                    qa=inspect_video(target)
                    record["salvaged_as"]=str(target.relative_to(folder))
            if qa:
                record["video_verified"]=qa
                playable.append(record["salvaged_as"] if record.get("salvaged_as") else record["name"])
        all_files.append(record)
    status="video_recovered" if playable else "video_unplayable" if broken_count else "no_video_available"
    return {"status":status,"files":all_files,"playable_videos":playable}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input-dir",type=Path,default=Path("outputs/recovery"))
    p.add_argument("--output",type=Path,default=Path("outputs/recovery/recovery-report.json"))
    args=p.parse_args()
    result=collect_media(args.input_dir)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("KAGGLE_RECOVERY_STATUS="+result["status"])
    print("KAGGLE_RECOVERY_MEDIA_FILES="+str(len(result["files"])))
    print("KAGGLE_RECOVERY_PLAYABLE_VIDEOS="+str(len(result["playable_videos"])))
    for name in result["playable_videos"]:
        print("RECOVERED_MP4="+name)


if __name__=="__main__":
    main()
