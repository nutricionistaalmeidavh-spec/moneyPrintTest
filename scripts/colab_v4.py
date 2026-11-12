"""Colab V4 interactive runner for MoneyPrint. Core stays free/self-hostable.

This module runs locally as well as in Colab. No secret, SaaS, API key or
external paid executor is necessary. Colab is an interactive compute option.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

FPS = 30
ALLOWED_ASPECTS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}


def call(args, **kwargs):
    return subprocess.run([str(x) for x in args], check=True, **kwargs)


def media_info(path):
    data = json.loads(subprocess.check_output(
        ["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format",
         "-of", "json", str(path)], text=True))
    v = next((x for x in data["streams"] if x["codec_type"] == "video"), None)
    a = next((x for x in data["streams"] if x["codec_type"] == "audio"), None)
    return {"duration": float(data["format"]["duration"]),
            "width": int(v["width"]) if v else None,
            "height": int(v["height"]) if v else None,
            "frames": int(v.get("nb_read_frames", 0)) if v else None,
            "audio": bool(a), "video": bool(v)}


def create_board(topic, script, aspect="16:9", visual_style="light_motion",
                 approved_assets=None):
    from scripts.studio_project import create_project, validate_project
    if aspect not in ALLOWED_ASPECTS:
        raise ValueError("Aspect ratio unsupported")
    if visual_style not in {"classic", "light_motion"}:
        raise ValueError("Only free Studio V3 styles supported")
    if not script or not script.strip():
        raise ValueError("An explicit script is required; no hidden LLM service")
    estimated = max(15, min(3600, math.ceil(len(script.split()) / 2.4)))
    board = create_project(topic=topic, script=script, duration_seconds=estimated,
                           fps=FPS, aspect=aspect, assets=approved_assets or [])
    board["visual_style"] = visual_style
    validate_project(board)
    return board


def sha_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def visual_cache_key(scene, board, root, width=None, height=None):
    """Key changes when scene data, a verified asset, or renderer changes."""
    asset = next((a for a in board.get("assets", [])
                  if a["id"] == scene.get("asset_id")), None)
    asset_sig = ""
    if asset:
        candidate = (Path(root) / asset["path"]).resolve()
        safe = (Path(root) / "assets").resolve()
        if not candidate.is_relative_to(safe) or not candidate.is_file():
            raise ValueError("Unapproved/missing visual asset")
        asset_sig = sha_file(candidate)
    renderer = Path(root) / "scripts" / "studio_render.py"
    engine_sig = sha_file(renderer)
    if board.get("visual_style") == "light_motion":
        light = Path(root) / "scripts" / "studio_light_motion.py"
        if light.exists():
            engine_sig += ":" + sha_file(light)
    default_width, default_height = ALLOWED_ASPECTS[board["aspect"]]
    width, height = width or default_width, height or default_height
    # Absolute position is not visual content: do not invalidate following scenes.
    visual_scene = {key: value for key, value in scene.items() if key != "start_frame"}
    payload = {"scene": visual_scene, "aspect": board["aspect"], "fps": board["fps"],
               "style": board["visual_style"], "assets": asset,
               "file_sha256": asset_sig, "renderer_sha256": engine_sig,
               "width": width, "height": height, "colab_pipeline_version": 4}
    return hashlib.sha256(json.dumps(payload, sort_keys=True,
                                     ensure_ascii=False).encode()).hexdigest()


def sync_frames(board, durations):
    """Update the sole canonical V3 timeline from real speech durations."""
    from scripts.studio_project import validate_project
    updated = copy.deepcopy(board)
    scenes = updated["scenes"]
    if len(scenes) != len(durations):
        raise ValueError("Audio count differs from storyboard")
    cursor = 0
    for scene, seconds in zip(scenes, durations):
        if not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds <= 0:
            raise ValueError("Invalid scene speech duration")
        count = math.ceil(float(seconds) * updated["fps"])
        if count < 1 or count > updated["fps"] * 3600:
            raise ValueError("Audio too long for a scene")
        scene["start_frame"] = cursor
        scene["duration_frames"] = count
        cursor += count
    updated["total_frames"] = cursor
    validate_project(updated)
    return updated


def _speech_engine(engine, reference_audio=None, reference_text=None):
    """Explicit, non-silent choice of offline text-to-speech backend."""
    if engine == "paradee":
        from scripts.paradee_voice import _build_engine
        sess, g2p, vocab = _build_engine("alex")
        return ("paradee", (sess, g2p, vocab))
    if engine == "qwen3":
        if not reference_audio or not Path(reference_audio).is_file() or not reference_text:
            raise ValueError("Qwen3 needs an authorized reference WAV and exact transcript")
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError("GPU required for experimental Qwen3 mode; choose Paradee for CPU")
        from qwen_tts import Qwen3TTSModel
        model = Qwen3TTSModel.from_pretrained(
            "Qwen/Qwen3-TTS-12Hz-0.6B-Base", device_map="cuda:0",
            dtype=torch.float16, attn_implementation="sdpa")
        prompt = model.create_voice_clone_prompt(
            ref_audio=str(reference_audio), ref_text=reference_text,
            x_vector_only_mode=False)
        return ("qwen3", (model, prompt))
    raise ValueError("Unknown voice backend; choose paradee or qwen3")


def create_narration(board, workdir, engine="paradee", speed=1.06,
                     reference_audio=None, reference_text=None):
    """Generate, silence-compact, frame-align and cache each speech scene."""
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly
    from scripts.paradee_voice import (MODEL_REVISION, make_tokens,
                                       split_text, silence_compact)
    if not .8 <= speed <= 1.25:
        raise ValueError("Voice speed out of range")
    workdir = Path(workdir)
    speech_dir = workdir / "speech"
    speech_dir.mkdir(parents=True, exist_ok=True)
    kind, impl = _speech_engine(engine, reference_audio, reference_text)
    target_rate = 24000
    all_audio, scene_reports, exact_durations = [], [], []
    ref_sig = sha_file(reference_audio) if engine == "qwen3" else ""
    for number, scene in enumerate(board["scenes"], 1):
        statement = scene["text"].strip()
        signature = (engine + "|" + MODEL_REVISION + "|" + str(speed) + "|" +
                     ref_sig + "|" + (reference_text or "") + "|" + statement)
        key = hashlib.sha256(signature.encode()).hexdigest()
        cached = speech_dir / (key + ".wav")
        if cached.is_file():
            wave, sample_rate = sf.read(cached, dtype="float32")
            if sample_rate != target_rate or wave.ndim != 1 or len(wave) < target_rate // 3:
                cached.unlink()
        if not cached.is_file():
            chunks = []
            if kind == "paradee":
                sess, g2p, vocab = impl
                for section in split_text(statement, max_chars=175):
                    phonemes, _ = g2p(section)
                    tokens = make_tokens(phonemes, vocab)
                    result = sess.run(None, {
                        "input_ids": np.array([tokens], dtype=np.int64),
                        "speed": np.array([speed], dtype=np.float32)})[0][0]
                    chunks.append(np.asarray(result, dtype=np.float32).reshape(-1))
                wave = np.concatenate(chunks)
            else:
                model, prompt = impl
                chunks = []
                for section in split_text(statement, max_chars=175):
                    result, sample_rate = model.generate_voice_clone(
                        text=section, language="Portuguese", voice_clone_prompt=prompt)
                    arr = np.asarray(result[0], dtype=np.float32).reshape(-1)
                    if sample_rate != target_rate:
                        gcd = math.gcd(sample_rate, target_rate)
                        arr = resample_poly(arr, target_rate // gcd,
                                            sample_rate // gcd).astype(np.float32)
                    chunks.append(arr)
                wave = np.concatenate(chunks)
            if not np.isfinite(wave).all() or len(wave) < target_rate // 3:
                raise RuntimeError("TTS generated invalid waveform: " + scene["id"])
            sf.write(cached, wave, target_rate, subtype="PCM_16")
        else:
            wave, _ = sf.read(cached, dtype="float32")
        cleaned, meta = silence_compact(wave, target_rate, max_pause=.38)
        if not len(cleaned) or not np.isfinite(cleaned).all():
            raise RuntimeError("Silence cleaning failed")
        frames = max(1, math.ceil(len(cleaned) * FPS / target_rate))
        exact_samples = round(frames * target_rate / FPS)
        clean = np.pad(cleaned, (0, max(0, exact_samples - len(cleaned))))[:exact_samples]
        peak = float(np.max(np.abs(clean)))
        if peak < .005:
            raise RuntimeError("Voice output nearly silent")
        clean = (clean * min(1.0, .91 / peak)).astype(np.float32)
        wave_path = speech_dir / f"scene_{number:03d}.wav"
        sf.write(wave_path, clean, target_rate, subtype="PCM_16")
        all_audio.append(clean)
        exact_durations.append(frames / FPS)
        scene_reports.append({"id": scene["id"], "seconds": frames / FPS,
                              "frames": frames, "cache_sha": key,
                              "removed_pause_seconds": meta["removed_seconds"]})
    combined = np.concatenate(all_audio)
    narration = workdir / "narracao_ptbr.wav"
    sf.write(narration, combined, target_rate, subtype="PCM_16")
    aligned = sync_frames(board, exact_durations)
    project_path = workdir / "storyboard_sincronizado.json"
    project_path.write_text(json.dumps(aligned, ensure_ascii=False, indent=2), encoding="utf-8")
    (workdir / "voz_diagnostico.json").write_text(
        json.dumps({"engine": engine, "scenes": scene_reports}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    return aligned, narration, scene_reports


def render_incremental(board, narration, root, output_dir, cache_dir=None,
                       width=None, height=None):
    """Re-render only changed Studio scenes. Uses existing FFmpeg/MoneyPrint render."""
    from scripts.studio_project import validate_project
    from scripts.studio_render import render_project
    root, output_dir = Path(root).resolve(), Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = Path(cache_dir or (output_dir / "cache")).resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    if not Path(narration).is_file():
        raise FileNotFoundError(narration)
    validate_project(board)
    dims = ALLOWED_ASPECTS[board["aspect"]]
    width = width or dims[0]
    height = height or dims[1]
    clips, reused, rendered = [], [], []
    for scene in board["scenes"]:
        key = visual_cache_key(scene, board, root, width=width, height=height)
        cached = cache_dir / (key + ".mp4")
        if not cached.is_file() or media_info(cached)["frames"] != scene["duration_frames"]:
            one = copy.deepcopy(board)
            one["scenes"] = [copy.deepcopy(scene)]
            one["scenes"][0]["start_frame"] = 0
            one["total_frames"] = scene["duration_frames"]
            validate_project(one)
            scratch = output_dir / ("render_" + scene["id"])
            result = render_project(one, root, scratch, voice="none",
                                    width=width, height=height, capture_github=False)
            shutil.copyfile(result["output"], cached)
            rendered.append(scene["id"])
        else:
            reused.append(scene["id"])
        clips.append(cached)
    playlist = output_dir / "segments.txt"
    # Generated cache filenames are SHA256 hex, never untrusted names.
    playlist.write_text("".join("file '" + str(clip) + "'\n" for clip in clips),
                        encoding="utf-8")
    picture = output_dir / "visual_sem_audio.mp4"
    call(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
          "-f", "concat", "-safe", "0", "-i", playlist, "-map", "0:v:0",
          "-c:v", "copy", "-an", picture])
    # MP4 concat demuxer may drop boundary frames due to varying edit lists.
    # Retain all cached scene content: only re-encode the *join*, never
    # re-render unchanged animations. Test the actual decoded frame count.
    joined = media_info(picture)
    if joined["frames"] != board["total_frames"]:
        normalized = output_dir / "visual_cfr_exato.mp4"
        graph = []
        args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y"]
        for idx, (clip, scene) in enumerate(zip(clips, board["scenes"])):
            args.extend(["-i", clip])
            graph.append(
                f"[{idx}:v:0]trim=start_frame=0:end_frame={scene['duration_frames']},"
                f"setpts=PTS-STARTPTS[v{idx}]")
        graph.append("".join(f"[v{idx}]" for idx in range(len(clips))) +
                     f"concat=n={len(clips)}:v=1:a=0[v]")
        args.extend(["-filter_complex", ";".join(graph), "-map", "[v]",
                     "-frames:v", str(board["total_frames"]),
                     "-r", str(board["fps"]), "-an", "-c:v", "libx264",
                     "-preset", "veryfast", "-crf", "20", "-threads", "3",
                     "-pix_fmt", "yuv420p", "-movflags", "+faststart", normalized])
        call(args)
        picture = normalized
    if media_info(picture)["frames"] != board["total_frames"]:
        raise RuntimeError("Scene join lost frames; refusing to publish")
    final = output_dir / "MoneyPrint_V4_Final.mp4"
    call(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
          "-i", picture, "-i", narration, "-map", "0:v:0", "-map", "1:a:0",
          "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
          "-ac", "2", "-movflags", "+faststart",
          "-t", f"{board['total_frames'] / board['fps']:.6f}", final])
    info = media_info(final)
    expected = board["total_frames"] / board["fps"]
    if not info["audio"] or not info["video"] or info["frames"] != board["total_frames"]:
        raise RuntimeError(f"Rendered movie failed the frame/audio QA: actual={info}, expected_frames={board['total_frames']}")
    if abs(info["duration"] - expected) > .25:
        raise RuntimeError("Narration/video sync exceeded 250ms")
    summary = {"output": str(final), "scenes_rendered": rendered,
               "scenes_reused": reused, "total_frames": board["total_frames"],
               "target_seconds": expected, "real_seconds": info["duration"]}
    (output_dir / "incremental.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def transcribe_words(movie, output_dir, model_size="small"):
    """Observed timestamps, never estimated words presented as actual."""
    from faster_whisper import WhisperModel
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    entries, _ = model.transcribe(str(movie), language="pt", vad_filter=True,
                                  word_timestamps=True, beam_size=3)
    rows = [{"start": round(s.start, 3), "end": round(s.end, 3),
             "text": s.text.strip(),
             "words": [{"start": round(w.start, 3), "end": round(w.end, 3),
                        "word": w.word} for w in (s.words or [])
                       if w.start is not None and w.end is not None]}
            for s in entries if s.text.strip()]
    (output_dir / "palavras_reais.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return rows


def audiovisual_qa(movie, board, output_dir, silence_limit=.75):
    """Report objective media properties and long silences; no inflated claims."""
    output_dir = Path(output_dir)
    info = media_info(movie)
    width, height = ALLOWED_ASPECTS[board["aspect"]]
    expected = board["total_frames"] / board["fps"]
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-i", str(movie),
           "-af", f"silencedetect=noise=-42dB:d={silence_limit}",
           "-f", "null", "-"]
    detector = subprocess.run(cmd, capture_output=True, text=True, check=False)
    pauses = [float(x) for x in re.findall(r"silence_duration:\s*([0-9.]+)",
                                           detector.stderr)]
    report = {"width": info["width"], "height": info["height"],
              "fps": board["fps"], "frames": info["frames"],
              "duration_seconds": info["duration"],
              "duration_diff_seconds": round(info["duration"] - expected, 3),
              "has_audio": info["audio"], "silences_over_threshold_seconds": pauses,
              "pass": info["audio"] and info["video"]
              and info["width"] == width and info["height"] == height
              and info["frames"] == board["total_frames"]
              and abs(info["duration"] - expected) <= .25
              and not any(p >= 1.0 for p in pauses),
              "note": "Automated QC checks timing/format/silence; visual typography and voice naturalness still require human approval."}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "qa_audio_video.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def export_generic_shorts(movie, output_dir, transcript, count=5,
                          min_duration=20.0, max_duration=55.0):
    """Create nonoverlapping 9:16 Shorts from observed sentence timestamps."""
    if not 1 <= count <= 10:
        raise ValueError("Invalid shorts count")
    from scripts.shorts_from_video import validate_segments
    duration = media_info(movie)["duration"]
    segments = validate_segments(transcript, duration)
    candidates = []
    for i, first in enumerate(segments):
        for j in range(i, len(segments)):
            last = segments[j]
            length = last["end"] - first["start"]
            if length > max_duration:
                break
            if length < min_duration:
                continue
            if any(segments[k+1]["start"] - segments[k]["end"] > 1.2
                   for k in range(i, j)):
                continue
            fullness = int(bool(re.search(r"[.!?]$", last["text"])))
            candidates.append((fullness * 8 - abs(length - 35) / 6,
                               first["start"], last["end"], i, j))
    ranked = sorted(candidates, reverse=True)
    selected = []
    for _, start, end, i, j in ranked:
        if any(start < a_end and end > a_start for a_start, a_end, *_ in selected):
            continue
        selected.append((start, end, i, j))
        if len(selected) == count:
            break
    if not selected:
        raise RuntimeError("No complete non-overlapping speech segments for Shorts")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for idx, (start, end, i, j) in enumerate(sorted(selected), 1):
        target = output_dir / f"MoneyPrint_Short_{idx:02d}_9x16.mp4"
        graph = ("[0:v]fps=30,split=2[bg0][main0];"
                 "[bg0]scale=1080:1920:force_original_aspect_ratio=increase,"
                 "crop=1080:1920,boxblur=28:3,eq=brightness=-0.13[bg];"
                 "[main0]scale=1020:1600:force_original_aspect_ratio=decrease[main];"
                 "[bg][main]overlay=(W-w)/2:(H-h)/2:shortest=1,format=yuv420p[v]")
        call(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
              "-ss", f"{start:.3f}", "-i", movie, "-t", f"{end-start:.3f}",
              "-filter_complex", graph, "-map", "[v]", "-map", "0:a:0",
              "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
              "-r", "30", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
              "-movflags", "+faststart", target])
        check = media_info(target)
        if (check["width"], check["height"]) != (1080, 1920) or not check["audio"]:
            raise RuntimeError("Shorts quality check failed")
        results.append({"path": str(target), "start": start, "end": end,
                        "seconds": check["duration"],
                        "topic": " ".join(x["text"] for x in segments[i:j+1])[:140]})
    (output_dir / "manifest.json").write_text(
        json.dumps({"autopublish": False, "clips": results}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    return results
