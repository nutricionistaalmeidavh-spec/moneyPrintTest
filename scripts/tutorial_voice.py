"""MoneyPrint: mix local Piper narration over the tutorial (no paid APIs)."""
from __future__ import annotations
import argparse
import json
import subprocess
from pathlib import Path

def media_info(path: Path) -> tuple[float, bool]:
    data = json.loads(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type",
         "-of", "json", str(path)], text=True))
    return float(data["format"]["duration"]), any(
        s.get("codec_type") == "audio" for s in data.get("streams", []))

def speech_tempo(voice_seconds: float, video_seconds: float, delay: float = 1.2) -> float:
    """Automatic pace matched to the visual cut, preserving all narrated words."""
    if min(voice_seconds, video_seconds) <= 0 or not 0 <= delay < video_seconds:
        raise ValueError("Duração de vídeo/voz ou atraso inválido")
    return round(max(1.08, voice_seconds / max(0.5, video_seconds - delay - 0.3)), 4)

def mix(video: Path, voice: Path, output: Path, delay: float = 1.2) -> dict:
    if not video.is_file() or not voice.is_file() or output.resolve() in {
        video.resolve(), voice.resolve()
    }:
        raise ValueError("Arquivos de entrada/saída inválidos")
    video_seconds, has_music = media_info(video)
    voice_seconds, _ = media_info(voice)
    pace = speech_tempo(voice_seconds, video_seconds, delay)
    output.parent.mkdir(parents=True, exist_ok=True)
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
               "-i", str(video), "-i", str(voice)]
    # Every render uses an actual Piper-generated narration; source microphone is excluded.
    voice_filter = (
        f"[1:a]aresample=48000,atempo={pace},highpass=f=95,lowpass=f=7600,"
        "acompressor=threshold=0.20:ratio=2.3:attack=5:release=85,"
        f"loudnorm=I=-15:TP=-1.5:LRA=9,adelay={round(delay*1000)}:all=1[voice]"
    )
    if has_music:
        filters = (voice_filter +
                   ";[0:a]aresample=48000,volume=0.13[bg];"
                   "[bg][voice]amix=inputs=2:duration=first:normalize=0,"
                   "alimiter=limit=0.95[final]")
    else:
        filters = voice_filter.replace("[voice]", "[final]")
    command += ["-filter_complex", filters, "-map", "0:v:0", "-map", "[final]",
                "-c:v", "copy", "-c:a", "aac", "-ar", "48000", "-b:a", "160k",
                "-t", str(video_seconds), "-map_metadata", "-1",
                "-movflags", "+faststart", str(output)]
    subprocess.run(command, check=True)
    return {"status": "ok", "video": str(output), "duration": round(video_seconds, 2),
            "voice_source": "piper_local", "voice_pace": pace,
            "original_capture_audio": "excluded", "auto_publish": False}

def main():
    cli = argparse.ArgumentParser(description="Narração jovem e enérgica — Piper local")
    cli.add_argument("--video", required=True, type=Path)
    cli.add_argument("--voice", required=True, type=Path)
    cli.add_argument("--output", required=True, type=Path)
    cli.add_argument("--delay", type=float, default=1.2)
    args = cli.parse_args()
    print(json.dumps(mix(args.video,args.voice,args.output,args.delay),
                     ensure_ascii=False,indent=2))
if __name__ == "__main__":
    main()
