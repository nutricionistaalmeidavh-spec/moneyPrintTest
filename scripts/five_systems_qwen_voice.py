"""MoneyPrint: real Qwen3 voice clone for the five-systems ORIGINAL Opus movie.

Voice: upstream Qwen3-TTS VoiceDesign sample 01_jovem_dinamico, not Piper.
Visual: original 25 Opus-motion scenes, taken unchanged from the approved MP4.
Each scene is retimed to its new spoken duration; full motion still plays, and
excessive pauses are removed. Uses CPU, FFmpeg, numpy, open-source Qwen.
No background music, voice services, auto-publish or paid APIs.
"""
from __future__ import annotations

import argparse
import gc
import json
import math
import re
import subprocess
from pathlib import Path

REFERENCE_NAME="01_jovem_dinamico"
VOICE_MODEL="Qwen/Qwen3-TTS-12Hz-0.6B-Base"
PROJECT_BOARD=Path("video-requests/five-systems-original-opus-2026.json")
ORIGINAL_VIDEO_NAME="five-systems-opus-original-5min.mp4"
FPS=30

def build_timeline(board,voice_durations):
    scenes=board.get("scenes",[])
    if len(scenes)!=25 or len(voice_durations)!=25 or board.get("fps")!=FPS:
        raise ValueError("Expect 25 original scenes from the Opus storyboard")
    cur=0; video_cursor=0; out=[]
    for i,(shot,length) in enumerate(zip(scenes,voice_durations),1):
        if not isinstance(length,(int,float)) or not math.isfinite(length) or length<1.3 or length>30:
            raise ValueError("Voice length invalid for scene "+str(i))
        frames=int(shot["min"])
        new_frames=max(45,math.ceil(float(length)*FPS))
        out.append({
            "scene":i,"motion":shot["motion"],"text":shot["say"],
            "start_frame":cur,"end_frame":cur+frames,"original_frames":frames,
            "start_seconds":cur/FPS,"original_seconds":frames/FPS,
            "new_frames":new_frames,"new_seconds":new_frames/FPS,
            "video_start_seconds":video_cursor/FPS,
            "video_end_seconds":(video_cursor+new_frames)/FPS,
            "speed":round(frames/new_frames,4),
        })
        video_cursor+=new_frames
        cur+=frames
    if cur!=9000:raise ValueError("Movie must have exactly 9000 original frames")
    return out

def compact_silence(data,sample_rate,max_pause=.23):
    """Remove non-speech gaps, preserving word boundaries with 55ms context.

    Conservative energy-based filter on clean synthetic Qwen audio. Max internal
    silent gap is 230 ms; it never removes audio classified as spoken.
    """
    import numpy as np
    x=np.asarray(data,dtype=np.float32).reshape(-1)
    if not np.isfinite(x).all() or len(x)<sample_rate*1.3:
        raise ValueError("Invalid synthetic voice")
    hop=max(1,round(sample_rate*.01))
    padded=np.pad(x,(0,(-len(x))%hop))
    frames=padded.reshape(-1,hop)
    rms=np.sqrt(np.mean(frames.astype(np.float64)**2,axis=1))
    # Adaptive level follows the VoiceDesign sample instead of hard-gating quiet words.
    threshold=max(.00075,float(np.quantile(rms,.9))*.025)
    active=rms>threshold
    active_ids=np.flatnonzero(active)
    if len(active_ids)<12:
        raise ValueError("Qwen output too quiet to reconstruct the narration")
    max_gap=round(max_pause*sample_rate/hop)
    segments=[]
    lo=int(active_ids[0]);hi=lo
    for frame in active_ids[1:]:
        if frame-hi>max_gap:
            segments.append((lo,hi+1))
            lo=int(frame)
        hi=int(frame)
    segments.append((lo,hi+1))
    parts=[]
    for idx,(a,b) in enumerate(segments):
        a0=max(0,a*hop-round(.055*sample_rate))
        b0=min(len(x),b*hop+round(.055*sample_rate))
        if parts:
            parts.append(np.zeros(round(.16*sample_rate),dtype=np.float32))
        parts.append(x[a0:b0])
    # Intro/tail at most ~0.12 s, not the seconds-long Opus/pad silence.
    y=np.concatenate([np.zeros(round(.065*sample_rate),dtype=np.float32),
                      *parts,np.zeros(round(.12*sample_rate),dtype=np.float32)])
    # Smooth only outer boundaries, leaving natural speech dynamics intact.
    fade=max(1,round(.008*sample_rate))
    if len(y)>2*fade:
        y[:fade]*=np.linspace(0,1,fade,dtype=np.float32)
        y[-fade:]*=np.linspace(1,0,fade,dtype=np.float32)
    removed=max(0,(len(x)-len(y))/sample_rate)
    return y,{"raw_seconds":round(len(x)/sample_rate,3),
              "clean_seconds":round(len(y)/sample_rate,3),
              "removed_seconds":round(removed,3),
              "groups":len(segments),"gate":round(threshold,5)}

def _run(args):
    subprocess.run([str(a) for a in args],check=True)

def _master_audio(clips,sr,out):
    import numpy as np
    import soundfile as sf
    all_audio=[]
    for path in clips:
        samples,rate=sf.read(path,dtype="float32")
        if rate!=sr:raise RuntimeError("Qwen changed sample rate between scenes")
        all_audio.append(samples)
    sf.write(out,np.concatenate(all_audio),sr,subtype="PCM_16")
    return sum(len(part) for part in all_audio)/sr

def _render_visual_scenes(board,source,segments,work,ffmpeg):
    clips=[]
    for row in segments:
        n=row["scene"]
        target=work/f"visual_{n:02d}.mp4"
        factor=row["new_frames"]/row["original_frames"]
        # Original frame content is preserved. We change playback speed,
        # never redraw or replace the MIT Opus animations.
        _run([ffmpeg,"-hide_banner","-loglevel","error","-nostdin","-y",
              "-ss",f'{row["start_seconds"]:.6f}',
              "-t",f'{row["original_seconds"]:.6f}',
              "-i",source,
              "-map","0:v:0","-an",
              "-vf",f"setpts=(PTS-STARTPTS)*{factor:.9f},fps={FPS}",
              "-frames:v",row["new_frames"],"-r",FPS,
              "-c:v","libx264","-crf","22","-preset","veryfast","-threads","3",
              "-pix_fmt","yuv420p","-movflags","+faststart",target])
        clips.append(target)
        print(f"Original Opus motion {n:02d}/25 retimed {row['original_seconds']:.2f}s -> {row['new_seconds']:.2f}s",flush=True)
    playlist=work/"concat_original_opus.txt"
    playlist.write_text("".join("file '"+str(f.resolve())+"'\n" for f in clips),encoding="utf-8")
    movie=work/"opus_original_retimed.mp4"
    _run([ffmpeg,"-hide_banner","-loglevel","error","-nostdin","-y",
          "-f","concat","-safe","0","-i",playlist,"-an","-c:v","copy",
          "-movflags","+faststart",movie])
    return movie

def build_video(board_file,source,reference,manifest_file,out,ffmpeg):
    import numpy as np
    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel

    board=json.loads(Path(board_file).read_text(encoding="utf-8"))
    manifest=json.loads(Path(manifest_file).read_text(encoding="utf-8"))
    anchor=next((x for x in manifest if x.get("name")==REFERENCE_NAME),None)
    if anchor is None or not anchor.get("text") or not Path(reference).is_file():
        raise RuntimeError("The original Qwen VoiceDesign reference sample is required")
    if not Path(source).is_file() or Path(source).stat().st_size<10_000_000:
        raise RuntimeError("The original 25-motion Opus MP4 is required")
    ref_audio,ref_sr=sf.read(reference,dtype="float32")
    if ref_sr!=24000 or not 10<len(ref_audio)/ref_sr<25:
        raise RuntimeError("Unexpected original Qwen VoiceDesign reference")
    if len(board.get("scenes",[]))!=25 or sum(s["min"] for s in board["scenes"])!=9000:
        raise RuntimeError("Original visual storyboard changed; refuse to generate")
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    work=out/"_render"
    work.mkdir(exist_ok=True)

    torch.set_num_threads(4)
    torch.set_num_interop_threads(2)
    torch.manual_seed(20261111)
    model=Qwen3TTSModel.from_pretrained(
        VOICE_MODEL,device_map="cpu",dtype=torch.bfloat16,
        attn_implementation="sdpa")
    voice_prompt=model.create_voice_clone_prompt(
        ref_audio=str(reference),ref_text=anchor["text"],x_vector_only_mode=False)
    sr_expected=None
    speech=[]
    qa_voice=[]
    lengths=[]
    for i,shot in enumerate(board["scenes"],1):
        text=shot["say"].strip()
        if not text:raise RuntimeError(f"Missing canonical text for scene {i}")
        wavs,sr=model.generate_voice_clone(
            text=text,language="Portuguese",voice_clone_prompt=voice_prompt)
        arr=np.asarray(wavs[0],dtype=np.float32).reshape(-1)
        if sr_expected is None:sr_expected=sr
        if sr!=sr_expected:raise RuntimeError("Qwen voice sample rate changed")
        clean,stats=compact_silence(arr,sr,max_pause=.23)
        if not np.isfinite(clean).all():raise RuntimeError("Invalid Qwen audio scene "+str(i))
        # Keep voice volume consistent between clips without severe compression.
        active=clean[np.abs(clean)>.008]
        rms=float(np.sqrt(np.mean(active**2))) if len(active)>sr*.3 else float(np.sqrt(np.mean(clean**2)))
        level=min(2.3,max(.65,.12/max(.004,rms)))
        peak=max(.1,float(np.max(np.abs(clean))))
        clean=(clean*min(level,.93/peak)).astype(np.float32)
        # Frame-align audio to the video; no 2s gaps between paragraphs.
        new_frames=max(45,math.ceil(len(clean)*FPS/sr))
        exact_samples=int(round(new_frames*sr/FPS))
        if len(clean)<exact_samples:
            clean=np.pad(clean,(0,exact_samples-len(clean)))
        else:
            clean=clean[:exact_samples]
        audio=work/f"qwen_scene_{i:02d}.wav"
        sf.write(audio,clean,sr,subtype="PCM_16")
        speech.append(audio)
        lengths.append(new_frames/FPS)
        qa_voice.append({"scene":i,"motion":shot["motion"],"words":len(text.split()),
                          "sample":REFERENCE_NAME,"voice_duration":round(new_frames/FPS,3),
                          "stats":stats,"gain":round(level,3)})
        print(f"Qwen3 original BR voice {i:02d}/25: {len(text.split())} words -> {new_frames/FPS:.2f}s, {stats['removed_seconds']}s dead air removed",flush=True)
        del wavs,arr,clean
        gc.collect()
    # Model not needed for visual retime, reduce memory usage before x264.
    del model,voice_prompt
    gc.collect()

    rows=build_timeline(board,lengths)
    original_visual=_render_visual_scenes(board,source,rows,work,ffmpeg)
    total_audio=out/"moneyprint_qwen3_narracao_sem_pausas.wav"
    duration=_master_audio(speech,sr_expected,total_audio)
    final=out/"moneyprint_5_sistemas_qwen3_opus_original.mp4"
    # Single AAC encoding for a seamless track: no 25 AAC encoder-delay gaps.
    _run([ffmpeg,"-hide_banner","-loglevel","error","-nostdin","-y",
          "-i",original_visual,"-i",total_audio,
          "-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac",
          "-b:a","192k","-ar","48000","-ac","2",
          "-movflags","+faststart","-shortest",final])
    total_visual=sum(row["new_frames"] for row in rows)/FPS
    if abs(total_visual-duration)>.04:raise RuntimeError("Qwen speech and Opus visuals desynchronized")
    if final.stat().st_size<4_000_000:raise RuntimeError("Missing final Qwen + Opus movie")
    report={
        "result":"rendered","reference":"Qwen3-TTS VoiceDesign original "+REFERENCE_NAME,
        "reference_source":"GitHub Actions artifact moneyprint-qwen3-ptbr-preview-43047161887",
        "model":VOICE_MODEL,"core_cost_brl":0,"paid_api_dependency":False,
        "autopublish":False,"original_opus_motions":25,
        "unique_motion_types":len({x["motion"] for x in board["scenes"]}),
        "original_video_duration_seconds":300,
        "updated_video_duration_seconds":round(total_visual,3),
        "audio_duration_seconds":round(duration,3),
        "removed_silence_seconds":round(sum(x["stats"]["removed_seconds"] for x in qa_voice),3),
        "speech_quality":"Qwen3 TTS synthetic, verify pronunciation in human QA",
        "scene_audio":qa_voice,"visual_retiming":rows}
    (out/"qa_qwen3_sem_silencios.json").write_text(
        json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("Qwen+Opus movie ready:",final,flush=True)
    print("Movie report:",json.dumps({k:v for k,v in report.items() if k not in ("scene_audio","visual_retiming")},ensure_ascii=False),flush=True)
    return final

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--board",type=Path,default=PROJECT_BOARD)
    p.add_argument("--original",type=Path,required=True)
    p.add_argument("--reference",type=Path,default=Path("voice-previews/01_jovem_dinamico.wav"))
    p.add_argument("--manifest",type=Path,default=Path("voice-previews/voice_options.json"))
    p.add_argument("--out",type=Path,default=Path("outputs/five-systems-qwen"))
    p.add_argument("--ffmpeg",default="ffmpeg")
    a=p.parse_args()
    build_video(a.board,a.original,a.reference,a.manifest,a.out,a.ffmpeg)

if __name__=="__main__":main()
