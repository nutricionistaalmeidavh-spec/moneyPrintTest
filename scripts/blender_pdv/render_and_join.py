#!/usr/bin/env python3
"""Scene-wise Blender rendering and strict FFprobe QA; never auto-publish."""
from __future__ import annotations
import argparse,json,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve()
ROOT=HERE.parents[2] if HERE.parent.name=='blender_pdv' else HERE.parents[1]

def run(command):return subprocess.run(command,check=True,text=True)

def probe(path):
    p=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-count_frames','-show_entries',
       'stream=width,height,r_frame_rate,nb_read_frames','-of','json',str(path)],check=True,capture_output=True,text=True)
    streams=json.loads(p.stdout)['streams']
    if len(streams)!=1:raise ValueError(f'No usable video stream: {path}')
    return streams[0]

def render(project,output,quality,selected,rendering=False,project_path=None):
    if not rendering:return
    blender=shutil.which('blender')
    if not blender:raise RuntimeError('Blender not installed. Install Blender 4.2+ locally (GPL). No fallback to 2D.')
    for s in project['scenes']:
        if selected not in ('all',s['id']):continue
        builder=ROOT/'scripts'/'blender_pdv'/'build_blender.py'
        if not builder.is_file():builder=ROOT/'scripts'/'build_blender.py'
        run([blender,'-b','--factory-startup','--python',str(builder),'--',
             '--scene',s['id'],'--quality',quality,'--animate','--output-dir',str(output),
             '--project',str(project_path or ROOT/'projects'/'pdv-artisys-blender-v1.json')])

def assemble(project,output,quality):
    clips=[]
    for s in project['scenes']:
        path=output/f'pdv_artisys_scene_{s["id"]}.mp4'
        if not path.is_file():raise RuntimeError(f'Incomplete package. Missing scene {s["id"]}: {path}')
        meta=probe(path)
        frames=int(meta.get('nb_read_frames') or 0)
        if frames!=s['duration_frames']:raise RuntimeError(f'Scene {s["id"]}: {frames} frames, expected {s["duration_frames"]}')
        if meta['r_frame_rate']!='30/1':raise RuntimeError(f'Scene {s["id"]}: fps mismatch')
        if [int(meta['width']),int(meta['height'])]!=project['resolution'][quality]:raise RuntimeError(f'Scene {s["id"]}: resolution mismatch')
        clips.append(path)
    f=output/'blender_concat.txt'
    f.write_text(''.join('file '+repr(str(p.resolve()))+'\n' for p in clips),encoding='utf-8')
    dest=output/'moneyprint_blender_clean_82s.mp4'
    run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(f),'-c','copy',str(dest)])
    final=probe(dest)
    if int(final['nb_read_frames'])!=project['total_frames']:raise RuntimeError('Join lost/duplicated frames')
    return dest

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--quality',choices=['preview','final'],default='preview')
    p.add_argument('--project',type=Path,default=ROOT/'projects'/'pdv-artisys-blender-v1.json')
    p.add_argument('--scene',default='all')
    p.add_argument('--render',action='store_true')
    p.add_argument('--assemble',action='store_true')
    p.add_argument('--output-dir',default=str(ROOT/'outputs'))
    opt=p.parse_args()
    project=json.loads(opt.project.read_text(encoding='utf8'))
    output=Path(opt.output_dir).resolve();output.mkdir(parents=True,exist_ok=True)
    render(project,output,opt.quality,opt.scene,opt.render,project_path=opt.project)
    if opt.assemble:print('Final assembled:',assemble(project,output,opt.quality))
    elif not opt.render:print('No action: specify --render and optionally --assemble.')

if __name__=='__main__':main()
