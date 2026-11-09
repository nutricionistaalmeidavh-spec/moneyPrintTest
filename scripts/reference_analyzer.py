"""Read-only reference video analysis for MoneyPrint Studio.

FFprobe and FFmpeg are required. OpenCV is optional for a low-confidence focal
region estimate; no cloud inference, paid API, or fabricated frame semantics.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
from pathlib import Path


class ReferenceError(ValueError):
    pass


def parse_cuts(stderr: str, duration: float) -> list[float]:
    if duration <= 0:
        raise ReferenceError("Duração da referência inválida")
    values = []
    for match in re.finditer(r"\bpts_time:\s*(-?\d+(?:\.\d+)?)", stderr):
        value = float(match.group(1))
        if 0.02 < value < duration - 0.02 and (not values or abs(values[-1] - value) > 0.08):
            values.append(round(value, 3))
    return sorted(set(values))


def describe_rhythm(cuts: list[float], duration: float) -> dict:
    if duration <= 0:
        raise ReferenceError("Duração inválida")
    ticks = [0.0] + sorted(t for t in cuts if 0 < t < duration) + [duration]
    lengths = [round(b - a, 3) for a, b in zip(ticks, ticks[1:])]
    median = round(statistics.median(lengths), 3)
    cadence = "rapido" if median <= 2.4 else "medio" if median <= 6 else "lento"
    return {"shot_count": len(lengths), "median_shot_seconds": median,
            "mean_shot_seconds": round(statistics.mean(lengths), 3),
            "min_shot_seconds": min(lengths), "max_shot_seconds": max(lengths),
            "shots_seconds": lengths, "cadence": cadence}


def _aspect(width: int, height: int) -> str:
    if height > width * 1.2:
        return "9:16"
    if width > height * 1.2:
        return "16:9"
    return "1:1"


def plan_reference(metadata: dict, cuts: list[float]) -> dict:
    width = int(metadata["width"])
    height = int(metadata["height"])
    duration = float(metadata["duration"])
    fps = float(metadata.get("fps", 0))
    if width <= 0 or height <= 0 or duration <= 0:
        raise ReferenceError("Metadados inválidos")
    return {"version": 1, "duration_seconds": round(duration, 3),
            "resolution": {"width": width, "height": height}, "fps": round(fps, 3),
            "aspect": _aspect(width, height), "cut_timestamps": cuts,
            "rhythm": describe_rhythm(cuts, duration),
            "framing": {"method": "metadata_only", "confidence": "low",
                        "orientation": _aspect(width, height),
                        "note": "Proporção real; enquadramento semântico não inferido sem detector."}}


def _fps(value: str) -> float:
    try:
        num, den = value.split("/")
        return float(num) / float(den) if float(den) else 0
    except (ValueError, ZeroDivisionError, AttributeError):
        return 0.0


def probe_video(source: Path) -> dict:
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,avg_frame_rate",
             "-show_entries", "format=duration", "-of", "json", str(source)],
            capture_output=True, text=True, check=True, timeout=40)
        raw = json.loads(proc.stdout)
        stream = raw["streams"][0]
        return {"width": int(stream["width"]), "height": int(stream["height"]),
                "duration": float(raw["format"]["duration"]),
                "fps": _fps(stream.get("avg_frame_rate", "0/1"))}
    except (OSError, subprocess.SubprocessError, IndexError, KeyError,
            ValueError, TypeError) as exc:
        raise ReferenceError("Não foi possível ler o vídeo local") from exc


def detect_cuts(source: Path, duration: float, threshold: float = 0.30) -> list[float]:
    if not 0.05 <= threshold <= 0.90:
        raise ReferenceError("Sensibilidade inválida")
    try:
        proc = subprocess.run([
            "ffmpeg", "-hide_banner", "-nostdin", "-i", str(source),
            "-vf", f"select='gt(scene,{threshold})',showinfo",
            "-an", "-f", "null", "-"
        ], capture_output=True, text=True, timeout=1800, check=False)
        if proc.returncode:
            raise ReferenceError("FFmpeg não analisou todos os frames")
        return parse_cuts(proc.stderr, duration)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ReferenceError("Análise de cortes indisponível") from exc


def estimate_focal_regions(source: Path, duration: float,
                           cuts: list[float], max_samples: int = 24) -> dict:
    """Optional CPU-only saliency proxy. Never call this face/object detection."""
    try:
        import cv2  # type: ignore
    except ImportError:
        return {"method": "metadata_only", "confidence": "low",
                "note": "OpenCV ausente; não identificamos sujeitos nem rostos."}
    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        return {"method": "metadata_only", "confidence": "low",
                "note": "Frames não disponíveis para heurística de saliência."}
    bounds = [0.0] + cuts + [duration]
    points = [(a+b)/2 for a,b in zip(bounds,bounds[1:])][:max_samples]
    regions = []
    try:
        for seconds in points:
            cap.set(cv2.CAP_PROP_POS_MSEC, float(seconds)*1000)
            ok, image = cap.read()
            if not ok:
                continue
            gray = cv2.cvtColor(cv2.resize(image, (256,144)), cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 80, 160)
            coords = cv2.findNonZero(edges)
            if coords is None:
                continue
            mean_x = float(coords[:,:,0].mean())/256.0
            mean_y = float(coords[:,:,1].mean())/144.0
            horizontal = "left" if mean_x < .38 else "right" if mean_x > .62 else "center"
            vertical = "top" if mean_y < .36 else "bottom" if mean_y > .64 else "middle"
            regions.append({"at_seconds": round(seconds,3), "focal_hint": horizontal+"-"+vertical})
    finally:
        cap.release()
    return {"method": "edge_density_heuristic", "confidence": "low",
            "samples": regions,
            "note": "Centro de detalhes visuais, não prova de objeto, pessoa ou tipo de plano."}


def analyze_reference(source: Path, *, threshold: float = .30,
                      inspect_framing: bool = True) -> dict:
    source = Path(source).resolve()
    if not source.is_file() or source.suffix.lower() not in (".mp4",".mov",".mkv",".webm"):
        raise ReferenceError("Referência de vídeo local inexistente ou incompatível")
    metadata = probe_video(source)
    cuts = detect_cuts(source, metadata["duration"], threshold)
    report = plan_reference(metadata, cuts)
    if inspect_framing:
        report["framing"] = estimate_focal_regions(source, metadata["duration"], cuts)
    report["file"] = source.name
    report["tooling"] = {"cuts": "ffmpeg_scene_select", "metadata": "ffprobe",
                         "focal_estimate": report["framing"]["method"]}
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Análise local de referência, sem enviar arquivo à nuvem")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--threshold", type=float, default=.30)
    args = parser.parse_args()
    report = analyze_reference(args.input, threshold=args.threshold)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(args.output))


if __name__ == "__main__":
    main()
