#!/usr/bin/env python3
"""Opt-in, offline-first video post-production. Python stdlib + FFmpeg."""
import argparse,json,pathlib,subprocess,shutil,sys
def run(args):
    subprocess.run(args,check=True)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True);p.add_argument("--output",required=True)
    p.add_argument("--hook");p.add_argument("--hook-seconds",type=float,default=3)
    p.add_argument("--width",type=int,default=1920);p.add_argument("--height",type=int,default=1080)
    p.add_argument("--fps",type=int,default=30);p.add_argument("--transition",choices=["cut","fade"],default="cut")
    a=p.parse_args()
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):p.error("FFmpeg/FFprobe required")
    if a.hook_seconds<=0 or a.fps<=0 or a.width<=0 or a.height<=0:p.error("Invalid dimensions or duration")
    output=pathlib.Path(a.output);output.parent.mkdir(parents=True,exist_ok=True)
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        def norm(source,dest,seconds=None):
            cmd=["ffmpeg","-y","-i",source]
            if seconds:cmd+=["-t",str(seconds)]
            cmd+=["-vf",f"scale={a.width}:{a.height}:force_original_aspect_ratio=decrease,pad={a.width}:{a.height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={a.fps}","-c:v","libx264","-pix_fmt","yuv420p","-an",dest]
            run(cmd)
        clips=[]
        if a.hook:
            hook=str(pathlib.Path(tmp)/"hook.mp4");norm(a.hook,hook,a.hook_seconds);clips.append(hook)
        body=str(pathlib.Path(tmp)/"body.mp4");norm(a.input,body);clips.append(body)
        concat=pathlib.Path(tmp)/"list.txt"
        concat.write_text("".join("file '"+c.replace("'","'\\''")+"'\n" for c in clips))
        joined=str(pathlib.Path(tmp)/"joined.mp4")
        run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),"-c:v","libx264","-pix_fmt","yuv420p",joined])
        # Preserve original body audio when no hook; with hook, delay audio by hook length.
        probe=subprocess.run(["ffprobe","-v","error","-select_streams","a:0","-show_entries","stream=index","-of","csv=p=0",a.input],capture_output=True,text=True,check=True)
        if probe.stdout.strip():
            delay=int(a.hook_seconds*1000) if a.hook else 0
            run(["ffmpeg","-y","-i",joined,"-i",a.input,"-filter_complex",f"[1:a]adelay={delay}:all=1[a]","-map","0:v:0","-map","[a]","-c:v","copy","-c:a","aac","-shortest",str(output)])
        else:shutil.copyfile(joined,output)
    print(json.dumps({"output":str(output),"hook":bool(a.hook),"transition":"hard_cut","fps":a.fps}))
if __name__=="__main__":main()
