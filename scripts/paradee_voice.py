"""Offline Paradee-8M Pt-BR ONNX voice, synced to the approved ORIGINAL Opus MP4.

Voice model: eraldohug/Paradee-8M-PtBr (Apache-2.0). No Qwen, no Piper,
no paid APIs, no GPU or hidden SaaS dependencies. The 25 original motions
are NEVER regenerated: FFmpeg retimes their decoded frames to match
natural, silence-compacted Brazilian Portuguese narration.

Default voice 'alex' (masculine); 'dora' is an explicit alternative.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

MODEL_REPO="eraldohug/Paradee-8M-PtBr"
MODEL_REVISION="413c93ca4bb77182e5c1962b7a8aded331da8a6a"
VOICE_FILES={
    "alex":"onnx/paradee_alex_int8.onnx",
    "dora":"onnx/paradee_dora_int8.onnx",
}
AUDIO_RATE=24000
FPS=30

def phonemes_from_g2p_result(result) -> str:
    """Normalize Misaki EspeakG2P variants returning text or (text, metadata).

    Some runtime versions return a plain phoneme string; unpacking it into
    `phonemes, _` raises ValueError when the string has >2 characters.
    """
    value = result[0] if isinstance(result, (tuple, list)) and result else result
    if not isinstance(value, str) or not value.strip():
        raise ValueError("EspeakG2P returned empty or invalid phonemes")
    return value


def make_tokens(phonemes:str,vocab:dict)->list[int]:
    """Original model-card tokenization; never truncate text silently."""
    token_ids=[int(vocab[c]) for c in phonemes if c in vocab]
    if len(token_ids)<3 or len(token_ids)>510:
        raise ValueError(f"Phoneme token count outside model limit: {len(token_ids)}")
    return [0]+token_ids+[0]

def split_text(text:str,max_chars=175)->list[str]:
    """Segment at word boundaries without rewriting the user's script."""
    text=re.sub(r"\s+"," ",text.strip())
    if not text:raise ValueError("Empty narration")
    out=[];line=""
    for word in text.split(" "):
        if len(word)>max_chars:raise ValueError("Very long word; cannot split safely")
        new=(line+" "+word).strip()
        if len(new)>max_chars and line:
            out.append(line);line=word
        else:line=new
    if line:out.append(line)
    return out

def visual_scene_ranges(board:dict)->list[dict]:
    scenes=board.get("scenes",[])
    if board.get("fps")!=FPS or len(scenes)!=25:
        raise ValueError("Require exact original 25-scene Opus storyboard at 30fps")
    result=[];cur=0
    for i,shot in enumerate(scenes,1):
        frames=int(shot.get("min",0))
        if frames<60 or shot.get("transition",{}).get("type")!="cut":
            raise ValueError(f"Unexpected original scene {i}")
        result.append({"index":i,"motion":shot["motion"],"frames":frames,
                       "start_frame":cur,"end_frame":cur+frames,
                       "say":shot["say"]})
        cur+=frames
    if cur!=9000:raise ValueError("Expected 9000 original Opus frames")
    return result

def silence_compact(signal,sample_rate:int,max_pause=.42):
    """Remove prolonged near-zero intervals conservatively (never trim speech).

    Keeps natural pauses <= max_pause and 70ms margin around voiced chunks.
    Returns clean PCM plus a detailed audit report.
    """
    import numpy as np
    x=np.asarray(signal,dtype=np.float32).reshape(-1)
    if len(x)<int(.4*sample_rate) or not np.isfinite(x).all():
        raise ValueError("Empty, too short or corrupt Paradee waveform")
    hop=max(1,round(sample_rate*.010))
    b=np.pad(x,(0,(-len(x))%hop)).reshape(-1,hop)
    rms=np.sqrt((b.astype(np.float64)**2).mean(axis=1))
    # Adaptive noise floor based on actual signal level. Avoid gating soft words.
    level=float(np.quantile(rms,.9))
    threshold=max(.0004,level*.018)
    indexes=np.flatnonzero(rms>threshold)
    if len(indexes)<12:raise ValueError("Voice audio contains almost no speech")
    bridge=max(1,round(max_pause*sample_rate/hop))
    groups=[]
    st=int(indexes[0]);prev=st
    for pos in indexes[1:]:
        pos=int(pos)
        if pos-prev>bridge:
            groups.append((st,prev+1))
            st=pos
        prev=pos
    groups.append((st,prev+1))
    parts=[]
    pad=round(.07*sample_rate)
    for i,(a,b) in enumerate(groups):
        lo=max(0,a*hop-pad)
        hi=min(len(x),b*hop+pad)
        part=x[lo:hi]
        if i:parts.append(np.zeros(round(min(.18,max_pause)*sample_rate),dtype=np.float32))
        parts.append(part)
    y=np.concatenate([np.zeros(round(.06*sample_rate),dtype=np.float32),
                      *parts,np.zeros(round(.14*sample_rate),dtype=np.float32)])
    if float(np.max(np.abs(y)))<.005:raise ValueError("Model produced silence")
    removed=max(0,(len(x)-len(y))/sample_rate)
    return y,{"original_seconds":round(len(x)/sample_rate,3),
              "new_seconds":round(len(y)/sample_rate,3),
              "removed_seconds":round(removed,3),
              "groups":len(groups),"threshold":round(threshold,6)}

def design_visual_splice(rows:list[dict],durations_frames:list[int])->dict:
    if len(rows)!=25 or len(durations_frames)!=25:
        raise ValueError("Must preserve 25 original motions")
    filters=["[0:v]split=25"+"".join(f"[src{k}]" for k in range(25))]
    target=0
    for i,(row,length) in enumerate(zip(rows,durations_frames)):
        if not isinstance(length,int) or length<45 or length>900:
            raise ValueError(f"Invalid voice-aligned scene duration {i+1}: {length}")
        r=length/row["frames"]
        filters.append(
            f"[src{i}]trim=start_frame={row['start_frame']}:end_frame={row['end_frame']},"
            f"setpts=(PTS-STARTPTS)*{r:.10f},fps={FPS},"
            f"tpad=stop_mode=clone:stop_duration=1,"
            f"trim=end_frame={length},setpts=PTS-STARTPTS[v{i}]")
        target+=length
    filters.append("".join(f"[v{i}]" for i in range(25))+"concat=n=25:v=1:a=0[v]")
    return {"filters":";\n".join(filters)+"\n","total_frames":target,
            "duration_seconds":target/FPS}

def _build_engine(voice:str):
    import numpy as np
    import onnxruntime as ort
    from huggingface_hub import hf_hub_download
    from misaki.espeak import EspeakG2P
    if voice not in VOICE_FILES:raise ValueError("Voice must be alex or dora")
    model=hf_hub_download(MODEL_REPO,VOICE_FILES[voice],revision=MODEL_REVISION)
    config_path=hf_hub_download(MODEL_REPO,"config.json",revision=MODEL_REVISION)
    licence=hf_hub_download(MODEL_REPO,"LICENSE",revision=MODEL_REVISION)
    if "Apache License" not in Path(licence).read_text(encoding="utf-8"):
        raise RuntimeError("License verification failed")
    vocab=json.loads(Path(config_path).read_text(encoding="utf-8"))["vocab"]
    if not isinstance(vocab,dict) or len(vocab)<80:raise RuntimeError("Invalid model vocabulary")
    session_options=ort.SessionOptions()
    session_options.intra_op_num_threads=2
    session_options.inter_op_num_threads=1
    session=ort.InferenceSession(model,sess_options=session_options,providers=["CPUExecutionProvider"])
    assert {inp.name for inp in session.get_inputs()}=={"input_ids","speed"}
    g2p=EspeakG2P(language="pt-br")
    return session,g2p,vocab

def synthesize(board,voice,speed,output,*,cache=None):
    import numpy as np
    import soundfile as sf
    rows=visual_scene_ranges(board)
    if voice not in VOICE_FILES:raise ValueError("Choose alex or dora")
    if not .8<=speed<=1.25:raise ValueError("Speed must be in range 0.8..1.25")
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    cache=Path(cache) if cache else output/"_voice_cache"
    cache.mkdir(parents=True,exist_ok=True)
    engine,g2p,vocab=_build_engine(voice)
    clips=[];durations=[];diagnostics=[]
    for row in rows:
        text=row["say"]
        key=hashlib.sha256((MODEL_REVISION+"|"+voice+"|"+str(speed)+"|"+text).encode("utf-8")).hexdigest()[:25]
        cached=cache/(key+".wav")
        if cached.exists():
            signal,rate=sf.read(cached,dtype="float32")
            if rate!=AUDIO_RATE or len(signal)<AUDIO_RATE*.4:cached.unlink()
        if not cached.exists():
            pieces=[]
            for chunk in split_text(text):
                phonemes=phonemes_from_g2p_result(g2p(chunk))
                tokens=make_tokens(phonemes,vocab)
                waveform=engine.run(None,{"input_ids":np.asarray([tokens],dtype=np.int64),
                                          "speed":np.asarray([speed],dtype=np.float32)})[0][0]
                wav=np.asarray(waveform,dtype=np.float32).reshape(-1)
                if not np.isfinite(wav).all():raise RuntimeError("Invalid model PCM")
                pieces.append(wav)
            signal=np.concatenate([np.zeros(round(.05*AUDIO_RATE),dtype=np.float32),
                                   *[part for k,wav in enumerate(pieces)
                                     for part in ((np.zeros(round(.10*AUDIO_RATE),dtype=np.float32),wav) if k else (wav,))],
                                   np.zeros(round(.10*AUDIO_RATE),dtype=np.float32)])
            sf.write(cached,signal,AUDIO_RATE,subtype="PCM_16")
        else:
            signal,rate=sf.read(cached,dtype="float32")
        clean,stats=silence_compact(signal,AUDIO_RATE,max_pause=.42)
        peak=float(np.max(np.abs(clean)))
        # Peak limiting without altering original prosody.
        clean=clean*min(1.0,.90/max(.001,peak))
        target_frames=max(45,math.ceil(len(clean)*FPS/AUDIO_RATE))
        samples=round(target_frames*AUDIO_RATE/FPS)
        clean=np.pad(clean,(0,max(0,samples-len(clean))))[:samples]
        clip=output/f"scene_{row['index']:02d}_{voice}.wav"
        sf.write(clip,clean,AUDIO_RATE,subtype="PCM_16")
        clips.append(clean);durations.append(target_frames)
        diagnostics.append({"scene":row["index"],"motion":row["motion"],
                            "words":len(text.split()),"new_frames":target_frames,
                            "new_seconds":target_frames/FPS,"audio":stats})
        print(f"Paradee {voice} {row['index']:02d}/25 — {target_frames/FPS:.2f}s"
              f" (redução pausa {stats['removed_seconds']:.2f}s)",flush=True)
    master=np.concatenate(clips)
    narration=output/f"moneyprint_paradee_{voice}_narracao.wav"
    sf.write(narration,master,AUDIO_RATE,subtype="PCM_16")
    if not .01<float(np.max(np.abs(master)))<1:
        raise RuntimeError("Bad narration dynamics")
    return narration,durations,diagnostics

def remux_original_opus(source,narration,board,frames,output,ffmpeg="ffmpeg"):
    output=Path(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    splice=design_visual_splice(visual_scene_ranges(board),frames)
    script=output.parent/"paradee_sync_25_original_opus.ffgraph"
    script.write_text(splice["filters"],encoding="utf-8")
    # Only FFmpeg decodes and retimes previously rendered frames.
    # This is NOT an Opus/React/Remotion motion render.
    subprocess.run([ffmpeg,"-hide_banner","-loglevel","error","-nostdin","-y",
       "-i",str(source),"-i",str(narration),
       "-filter_complex_script",str(script),"-map","[v]","-map","1:a:0",
       "-c:v","libx264","-preset","veryfast","-crf","23","-threads","3",
       "-r",str(FPS),"-pix_fmt","yuv420p",
       "-c:a","aac","-b:a","160k","-ar","48000","-ac","2",
       "-movflags","+faststart","-shortest",str(output)],check=True)
    if output.stat().st_size<2_000_000:raise RuntimeError("Incomplete movie")
    return splice

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--board",type=Path,required=True)
    p.add_argument("--original",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--voice",choices=list(VOICE_FILES),default="alex")
    p.add_argument("--speed",type=float,default=1.08)
    p.add_argument("--cache",type=Path)
    p.add_argument("--ffmpeg",default="ffmpeg")
    args=p.parse_args()
    if not args.original.is_file():raise FileNotFoundError(args.original)
    board=json.loads(args.board.read_text(encoding="utf-8"))
    narration,frames,diagnostics=synthesize(board,args.voice,args.speed,args.out,cache=args.cache)
    movie=args.out/f"moneyprint_opus_paradee_{args.voice}_ptbr.mp4"
    timing=remux_original_opus(args.original,narration,board,frames,movie,ffmpeg=args.ffmpeg)
    report={"status":"produced","provider":"paradee-8m-ptbr",
            "model":MODEL_REPO,"revision":MODEL_REVISION,"license":"Apache-2.0",
            "voice":args.voice,"sample_rate":AUDIO_RATE,"speed":args.speed,
            "original_opus_frames":9000,"motion_rerender_count":0,
            "original_motion_count":25,"motion_library_called":False,
            "voice_only_reproduction":True,
            "audio_video_synchronized":True,
            "output_frames":timing["total_frames"],
            "output_seconds":round(timing["duration_seconds"],3),
            "core_cost_brl":0,"no_paid_api":True,"autopublish":False,
            "original_scenes":diagnostics}
    (args.out/"qa_paradee_voz.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Paradee Original Opus final:",movie,flush=True)
    print(json.dumps({k:v for k,v in report.items() if k!="original_scenes"},ensure_ascii=False),flush=True)
    return movie

if __name__=="__main__":main()
