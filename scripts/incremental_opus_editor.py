"""Selective native Opus repair and FFmpeg *A/V* silence cuts.

Uses the canonical 25-scene MoneyPrint storyboard.  A repaired motion is
rendered by the ORIGINAL Opus React CLI before running this module.  For
the other 23 scenes reuse cached FFmpeg-normalized clips extracted from
the source master: no React/Opus/Remotion render of accepted scenes.

Audio silence removal edits video and audio at the SAME frame boundaries
and never erases spoken language, unlike silenceremove on audio alone.
A generic FFmpeg backend makes the splice reproducible without paid APIs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

FPS=30
WIDTH=1920
HEIGHT=1080
ENCODER_VERSION="h264-30-crf21-v2"

def _run(command,**kwargs):
    return subprocess.run([str(a) for a in command],check=True,**kwargs)

def _probe(file,count=False):
    cmd=["ffprobe","-v","error","-show_streams","-show_format","-of","json"]
    if count:cmd+=["-count_frames"]
    cmd.append(str(file))
    return json.loads(subprocess.check_output(cmd,text=True))

def _video_info(file,count=False):
    data=_probe(file,count)
    v=next((s for s in data["streams"] if s.get("codec_type")=="video"),None)
    if not v:raise ValueError(f"Source has no video stream: {file}")
    a=next((s for s in data["streams"] if s.get("codec_type")=="audio"),None)
    frames=int(v["nb_read_frames"]) if count and v.get("nb_read_frames") else None
    # FFprobe may reduce a CFR 30fps stream's average rate to a
    # near-30 rational after concat: e.g. 138147840/4604873.
    # The r_frame_rate describes the true per-frame timebase.
    from fractions import Fraction
    fps=v.get("r_frame_rate") or v.get("avg_frame_rate","")
    try:
        rate=float(Fraction(fps))
    except (ValueError,ZeroDivisionError):
        raise ValueError(f"Unrecognised source frame rate: {fps}") from None
    if not math.isfinite(rate) or abs(rate-30)>.02:
        raise ValueError(f"Source FPS must be 30: {fps}")
    return {"width":int(v.get("width",0)),"height":int(v.get("height",0)),
            "fps":fps,"frames":frames,"audio":bool(a),
            "seconds":float(data["format"]["duration"])}

def build_scene_spans(board,timing=None):
    shots=board.get("scenes",[])
    if len(shots)!=25 or board.get("fps")!=FPS:
        raise ValueError("The 25-scene original Opus storyboard is required")
    if sum(int(x.get("min",0)) for x in shots)!=9000:
        raise ValueError("The canonical movie must contain 9000 original frames")
    start=0
    for n,s in enumerate(shots,1):
        if s.get("transition",{}).get("type")!="cut":
            raise ValueError(f"Scene {n} is not a hard cut")
    spans=[]
    for n,shot in enumerate(shots,1):
        frames=int(shot["min"])
        spans.append({"index":n,"start_frame":start,"end_frame":start+frames,
                      "frames":frames,"motion":shot["motion"]})
        start+=frames
    if timing is None:return spans
    # Optional Qwen postproduction timing: source's *actual* scene boundaries,
    # not 12-second assumptions. Retime only the repaired motion to the same
    # final duration as the new narration; cache all untouched Qwen scenes.
    # Qwen used visual_retiming; the approved Paradee ONNX film exposes
    # original_scenes with new_frames. Either is an explicit, audited map.
    rows=timing.get("original_scenes") or timing.get("visual_retiming")
    if not isinstance(rows,list) or len(rows)!=25:
        raise ValueError("Missing scene-specific timing from approved voice master")
    cursor=0
    revised=[]
    for expected,row in zip(spans,rows):
        if int(row["scene"])!=expected["index"] or row["motion"]!=expected["motion"]:
            raise ValueError("Audio timing belongs to a different Opus storyboard")
        new_frames=int(row["new_frames"])
        if new_frames<45 or new_frames>900:
            raise ValueError("Retime out of range")
        revised.append({**expected,"start_frame":cursor,"end_frame":cursor+new_frames,
                        "frames":new_frames})
        cursor+=new_frames
    if "output_frames" in timing and int(timing["output_frames"])!=cursor:
        raise ValueError("Scene timings do not cover the approved Paradee MP4")
    return revised

def validate_patch(board,patch):
    spans=build_scene_spans(board)
    overrides=patch.get("scene_overrides")
    if not isinstance(overrides,dict) or not overrides:
        raise ValueError("No patch scenes declared")
    if len(overrides)>5:
        raise ValueError("Selective repair cannot accidentally rerender most of the film")
    selected={}
    allowed_motion_ids={shot["motion"] for shot in board["scenes"]}|{"notification-stack","device-mockup"}
    for key,item in overrides.items():
        if not str(key).isdigit():raise ValueError("Scene IDs must be decimal numbers")
        n=int(key)
        if n<2 or n>len(spans):
            raise ValueError("Scene outside safe 2..25 range")
        if not isinstance(item,dict) or not isinstance(item.get("props"),dict):
            raise ValueError(f"Missing original Opus props at scene {n}")
        motion=item.get("motion")
        if not isinstance(motion,str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)+",motion):
            raise ValueError("Invalid original Opus motion ID")
        if motion not in allowed_motion_ids:
            raise ValueError("Unknown upstream original Opus motion: "+motion)
        selected[n]=item
    return selected

def spec_duration_frames(spec):
    return sum(x["duration"] for x in spec.get("scenes",[]))

def generate_single_scene_specs(board,patch,dest):
    dest=Path(dest);dest.mkdir(parents=True,exist_ok=True)
    selected=validate_patch(board,patch)
    out={}
    for n,item in selected.items():
        original=board["scenes"][n-1]
        spec={"width":board["width"],"height":board["height"],"fps":board["fps"],
              "background":board.get("background","#F6F1E7"),
              "scenes":[{"motion":item["motion"],"props":item["props"],
                         "duration":original["min"],
                         "transition":{"type":"cut"}}],
              "overlays":[],"captions":[],"audio":{"sfx":[],"musicCues":[]}}
        target=dest/f"scene_{n:02d}.json"
        target.write_text(json.dumps(spec,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        out[n]=target
    return out

def parse_silencedetect(log,duration):
    """Parse FFmpeg silencedetect output (start/end may be on separate lines)."""
    lines=log.splitlines()
    ranges=[]
    start=None
    for line in lines:
        match=re.search(r"silence_start:\s*([-0-9.]+)",line)
        if match:start=max(0,float(match.group(1)))
        match=re.search(r"silence_end:\s*([-0-9.]+)",line)
        if match and start is not None:
            end=min(float(match.group(1)),duration)
            if end>start:ranges.append((start,end))
            start=None
    if start is not None and start<duration:ranges.append((start,duration))
    return ranges

def make_cut_plan(silences,duration,*,fps=FPS,min_gap=.65,pad=.18):
    if min_gap<=0 or pad<0:raise ValueError("Bad silence policy")
    cuts=[]
    last=0
    total=round(duration*fps)
    for start,end in sorted(silences):
        if end-start<min_gap:continue
        # Keep two breathing margins and do not clip the first/last frame.
        first=max(1,math.ceil((start+pad)*fps))
        final=min(total-1,math.floor((end-pad)*fps))
        if first<=last or final<=first+2:continue
        cuts.append((first,final))
        last=final
    return cuts

def build_keep_plan(cuts,total_frames):
    pos=0
    keeps=[]
    for a,b in cuts:
        if a<pos or b>total_frames or b<=a:
            raise ValueError("Invalid overlapping audio/video silence cuts")
        if a>pos:keeps.append((pos,a))
        pos=b
    if pos<total_frames:keeps.append((pos,total_frames))
    return keeps

def reusable_cache_key(source_sha,index,start_frame,duration_frames,profile=ENCODER_VERSION):
    digest=f"{source_sha}|{index}|{start_frame}|{duration_frames}|{profile}"
    return hashlib.sha256(digest.encode()).hexdigest()[:20]

def file_sha(file):
    h=hashlib.sha256()
    with Path(file).open("rb") as f:
        for b in iter(lambda:f.read(4*1024*1024),b""):h.update(b)
    return h.hexdigest()

def analyze_audio_silences(source,*,threshold_db=-38,min_duration=.68):
    p=subprocess.run(["ffmpeg","-hide_banner","-nostdin","-i",str(source),
                      "-vn","-af",f"silencedetect=noise={threshold_db}dB:d={min_duration}",
                      "-f","null","-"],text=True,capture_output=True,check=True)
    duration=_video_info(source)["seconds"]
    return parse_silencedetect(p.stderr,duration)

def _assert_valid_scene(path,frames):
    info=_video_info(path,count=True)
    if info["frames"]!=frames:
        raise ValueError(f"Scene has {info['frames']} frames instead of {frames}: {path}")
    if info["width"]!=WIDTH or info["height"]!=HEIGHT:
        raise ValueError("Scene is not FullHD")
    if info["audio"]:
        raise ValueError("Scene clips must be video only")
    return info

def _normalize_scene(src,dest,*,start_frame,source_frames,target_frames,patched):
    dest.parent.mkdir(parents=True,exist_ok=True)
    if patched:
        speed=target_frames/source_frames
        vf=(f"scale={WIDTH}:{HEIGHT}:flags=bicubic,"
            f"setpts=(PTS-STARTPTS)*{speed:.9f},fps={FPS},"
            f"tpad=stop_mode=clone:stop_duration=1,trim=end_frame={target_frames},"
            f"setpts=PTS-STARTPTS,format=yuv420p")
        inp=["-i",str(src)]
    else:
        # Decoder seeks to the previous keyframe and decodes to exact timestamp;
        # this is NOT a motion rerender. Reuse cached outputs on later edits.
        vf=(f"scale={WIDTH}:{HEIGHT}:flags=bicubic,fps={FPS},"
            f"trim=end_frame={target_frames},setpts=PTS-STARTPTS,format=yuv420p")
        inp=["-ss",f"{start_frame/FPS:.9f}","-i",str(src)]
    cmd=["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",*inp,
         "-map","0:v:0","-an","-vf",vf,"-frames:v",str(target_frames),"-r",str(FPS),
         "-c:v","libx264","-preset","veryfast","-crf","21",
         "-threads","3","-pix_fmt","yuv420p","-movflags","+faststart",str(dest)]
    _run(cmd)
    _assert_valid_scene(dest,target_frames)
    return dest

def _concat_scene_video(clips,output,working):
    playlist=working/"concat_reused_and_repaired.txt"
    playlist.write_text("".join("file '"+str(f.resolve()).replace("'","'\\''")+"'\n" for f in clips),
                        encoding="utf-8")
    _run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
          "-f","concat","-safe","0","-i",playlist,"-an",
          "-c:v","copy","-movflags","+faststart",output])
    return output

def _mux_original_audio(video,source,out,total_frames):
    _run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
          "-i",video,"-i",source,"-map","0:v:0","-map","1:a:0",
          "-c:v","copy","-c:a","aac","-ar","48000","-b:a","192k",
          "-t",f"{total_frames/FPS:.9f}","-movflags","+faststart",out])
    return out

def _cut_silence_from_both_streams(src,dest,cuts,total_frames,work):
    keep=build_keep_plan(cuts,total_frames)
    if not cuts:
        _run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
              "-i",src,"-c","copy","-movflags","+faststart",dest])
        return keep
    # Frame-aligned trim on both streams. Using FFmpeg silenceremove on only
    # the audio would desynchronize the animation, so NEVER do that.
    filters=["[0:v]split="+str(len(keep))+"".join(f"[vs{k}]" for k in range(len(keep))),
             "[0:a]asplit="+str(len(keep))+"".join(f"[as{k}]" for k in range(len(keep)))]
    for k,(start,end) in enumerate(keep):
        filters.append(
            f"[vs{k}]trim=start_frame={start}:end_frame={end},setpts=PTS-STARTPTS[v{k}]")
        filters.append(
            f"[as{k}]atrim=start={start/FPS:.9f}:end={end/FPS:.9f},"
            f"asetpts=PTS-STARTPTS[a{k}]")
    inp="".join(f"[v{k}][a{k}]" for k in range(len(keep)))
    filters.append(f"{inp}concat=n={len(keep)}:v=1:a=1[v][a]")
    script=work/"silence_audio_and_video.ffgraph"
    script.write_text(";\n".join(filters)+"\n",encoding="utf-8")
    expected_frames=sum(b-a for a,b in keep)
    _run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y","-i",src,
          "-filter_complex_script",script,"-map","[v]","-map","[a]",
          "-frames:v",str(expected_frames),"-r",str(FPS),
          "-c:v","libx264","-crf","22","-preset","veryfast","-threads","3",
          "-pix_fmt","yuv420p","-c:a","aac","-ar","48000","-b:a","192k",
          "-movflags","+faststart",dest])
    return keep

def assemble(board,patch,source,rendered_dir,out,cache_dir,*,timing=None,trim_silence=True):
    source=Path(source);rendered_dir=Path(rendered_dir);out=Path(out)
    cache_dir=Path(cache_dir)
    out.mkdir(parents=True,exist_ok=True)
    spans=build_scene_spans(board,timing=timing)
    selected=validate_patch(board,patch)
    source_meta=_video_info(source,count=True)
    if not source_meta["audio"] or source_meta["width"]!=WIDTH or source_meta["height"]!=HEIGHT:
        raise ValueError("Expected approved FullHD original with audio")
    expected_total=sum(s["frames"] for s in spans)
    if source_meta["frames"]!=expected_total:
        raise ValueError(f"Original source has {source_meta['frames']} not {expected_total} frames")
    hash_of_source=file_sha(source)
    working=out/"_work"
    working.mkdir(parents=True,exist_ok=True)
    clips=[]
    reused=0;normalized=0
    for scene in spans:
        n=scene["index"]
        selected_patch=selected.get(n)
        if selected_patch:
            original_scene=board["scenes"][n-1]
            src=rendered_dir/f"scene_{n:02d}.mp4"
            if not src.is_file():
                raise FileNotFoundError(f"Original Opus scene {n} not rendered: {src}")
            signature=hashlib.sha256(json.dumps(selected_patch,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
            key=reusable_cache_key(signature,n,0,scene["frames"],ENCODER_VERSION+"-patch")
            original_frames=int(original_scene["min"])
            _assert_valid_scene(src,original_frames)
        else:
            src=source
            key=reusable_cache_key(hash_of_source,n,scene["start_frame"],scene["frames"])
            original_frames=scene["frames"]
        target=cache_dir/f"scene_{n:02d}_{key}.mp4"
        if target.is_file():
            try:_assert_valid_scene(target,scene["frames"])
            except (ValueError,subprocess.CalledProcessError):target.unlink()
        if target.is_file():
            reused+=1
        else:
            _normalize_scene(src,target,start_frame=scene["start_frame"],
                             source_frames=original_frames,target_frames=scene["frames"],
                             patched=bool(selected_patch))
            normalized+=1
        clips.append(target)
        print(f"{n:02d}/25: {'MOTION ORIGINAL CORRIGIDO' if selected_patch else 'CENA APROVADA'} | {'CACHE' if target.is_file() and target.stat().st_size else 'CODEC'}",flush=True)
    silent_video=working/"approved_video_plus_repairs.mp4"
    _concat_scene_video(clips,silent_video,working)
    intermediate=working/"pre_corte_silencio.mp4"
    _mux_original_audio(silent_video,source,intermediate,expected_total)
    if trim_silence:
        p=patch.get("silence_cut",{})
        threshold=float(p.get("threshold_db",-38))
        min_gap=float(p.get("min_gap_seconds",.68))
        pad=float(p.get("pad_seconds",.18))
        intervals=analyze_audio_silences(intermediate,threshold_db=threshold,min_duration=min_gap)
        cuts=make_cut_plan(intervals,expected_total/FPS,min_gap=min_gap,pad=pad)
    else:
        intervals=[];cuts=[]
    final=out/"moneyprint_incremental_opus_sem_silencios.mp4"
    keep=_cut_silence_from_both_streams(intermediate,final,cuts,expected_total,working)
    final_info=_video_info(final,count=True)
    expected_frames=sum(b-a for a,b in keep)
    if final_info["frames"]!=expected_frames:
        raise RuntimeError("Audio/video cut produced an incorrect number of frames")
    if not final_info["audio"]:
        raise RuntimeError("Final movie lost the original voice")
    report={
        "result":"success","operation":"incremental-original-opus-repair",
        "source_sha256":hash_of_source,"source_run_id":patch.get("source_run_id"),
        "source_file":str(source),"source_frames":expected_total,
        "selected_original_opus_scenes":sorted(selected),
        "untouched_scenes_reused":25-len(selected),
        "normalized_cache_hits":reused,"normalized_cache_misses":normalized,
        "motion_rerender_count":len(selected),"motion_rerendered_with":"Opus original cli/mgl.mjs compose",
        "no_python_motion_redraw":True,
        "silence_intervals_detected":len(intervals),"silence_cuts":cuts,
        "silence_removed_frames":sum(b-a for a,b in cuts),
        "removed_seconds":round(sum(b-a for a,b in cuts)/FPS,3),
        "final_frames":final_info["frames"],"duration_seconds":round(final_info["frames"]/FPS,3),
        "audio_video_cut_together":True,"autopublish":False,
        "core_paid_dependency":False,
    }
    (out/"diagnostico_incremental.json").write_text(
        json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("INCREMENTAL MONEYPRINT:",json.dumps(report,ensure_ascii=False),flush=True)
    return final

def main():
    cli=argparse.ArgumentParser()
    sub=cli.add_subparsers(dest="command",required=True)
    prepare=sub.add_parser("prepare",help="only selected original Opus specs")
    prepare.add_argument("--board",type=Path,required=True)
    prepare.add_argument("--patch",type=Path,required=True)
    prepare.add_argument("--specs",type=Path,required=True)
    edit=sub.add_parser("assemble",help="reuse approved clips and replace selected scenes")
    edit.add_argument("--board",type=Path,required=True)
    edit.add_argument("--patch",type=Path,required=True)
    edit.add_argument("--source",type=Path,required=True)
    edit.add_argument("--rendered-dir",type=Path,required=True)
    edit.add_argument("--cache-dir",type=Path,required=True)
    edit.add_argument("--out",type=Path,required=True)
    edit.add_argument("--timing-json",type=Path)
    edit.add_argument("--no-trim-silence",action="store_true")
    args=cli.parse_args()
    board=json.loads(args.board.read_text(encoding="utf-8"))
    patch=json.loads(args.patch.read_text(encoding="utf-8"))
    if args.command=="prepare":
        result=generate_single_scene_specs(board,patch,args.specs)
        print("Only original Opus scenes:",sorted(result),flush=True)
    else:
        timing=json.loads(args.timing_json.read_text(encoding="utf-8")) if args.timing_json else None
        assemble(board,patch,args.source,args.rendered_dir,args.out,args.cache_dir,
                 timing=timing,trim_silence=not args.no_trim_silence)

if __name__=="__main__":main()
