#!/usr/bin/env python3
"""Create a seven-second authentic, caption-free PDV display texture from source.

This is an editorial selection of original footage, not a synthetic interface.
Hard cuts omit the creator's large tutorial captions. Self-hosted FFmpeg only.
"""
from __future__ import annotations
import argparse, hashlib, json, subprocess
from pathlib import Path

SEGMENTS = ((3, 6), (12, 16))
FRAMES=210
FPS=30

def ffprobe(path):
    raw=subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-count_frames',
       '-show_entries','stream=width,height,r_frame_rate,nb_read_frames,nb_frames',
       '-of','json',str(path)],text=True)
    return json.loads(raw)['streams'][0]

def make(src:Path,dst:Path,report:Path):
    src,dst,report=map(Path,(src,dst,report))
    if not src.is_file():raise FileNotFoundError(src)
    meta=ffprobe(src)
    if meta['r_frame_rate']!='30/1' or int(meta['width'])!=1080 or int(meta['height'])!=1920:
        raise ValueError('A fonte foi alterada: vídeo deve ser 1080x1920 a 30 FPS')
    dst.parent.mkdir(parents=True,exist_ok=True)
    report.parent.mkdir(parents=True,exist_ok=True)
    # Source has thick black side borders and instructional captions.
    # Retain only real GUI, and keep aspect ratio in a 1080×1920 display.
    filters=(
        '[0:v]trim=start=3:end=6,setpts=PTS-STARTPTS[s1];'
        '[0:v]trim=start=12:end=16,setpts=PTS-STARTPTS[s2];'
        '[s1][s2]concat=n=2:v=1:a=0,'
        'crop=744:1650:92:0,'
        'scale=1080:1920:force_original_aspect_ratio=decrease:flags=lanczos,'
        'pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x0b1524,'
        'fps=30,format=yuv420p[v]'
    )
    subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',str(src),
        '-filter_complex',filters,'-map','[v]','-an','-c:v','libx264',
        '-crf','18','-preset','medium','-movflags','+faststart','-frames:v',str(FRAMES),str(dst)],check=True)
    out=ffprobe(dst)
    if int(out['nb_read_frames'])!=FRAMES or out['r_frame_rate']!='30/1' or (int(out['width']),int(out['height']))!=(1080,1920):
        raise RuntimeError('A textura precisa ter exatamente 210 frames em 1080x1920 a 30fps')
    digest=lambda path:hashlib.file_digest(open(path,'rb'),'sha256').hexdigest()
    result={'status':'screen_texture_rendered_not_blender_3d','scene':'05','input':str(src),
      'source_sha256':digest(src),'output':str(dst),'output_sha256':digest(dst),
      'trim_segments_seconds':[list(x) for x in SEGMENTS],
      'removed_audio':True,'ui_preserved_from_real_video':True,'no_synthetic_ui':True,
      'output_frames':FRAMES,'fps':FPS,'output_size':[1080,1920],
      '3d_render_completed':False,'autopublish':False}
    report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--dest',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(make(args.source,args.dest,args.report),ensure_ascii=False,indent=2))
