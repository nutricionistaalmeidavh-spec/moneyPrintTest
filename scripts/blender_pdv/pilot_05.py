#!/usr/bin/env python3
"""One-command scene 05 self-hosted build; install Quaternius Standard and run Blender.

Never auto-publish. Never substitute procedural/cartoon PNGs if actual assets fail.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve()
ROOT=HERE.parents[2] if HERE.parent.name=='blender_pdv' else HERE.parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
if HERE.parent.name=='blender_pdv':
    from scripts.blender_pdv.quaternius_assets import (
        AssetError,install_standard_zip,find_standard_assets,
        STANDARD_BASE_SHA256,STANDARD_ANIM_SHA256)
else:
    from scripts.quaternius_assets import (
        AssetError,install_standard_zip,find_standard_assets,
        STANDARD_BASE_SHA256,STANDARD_ANIM_SHA256)


def media_probe(path: Path) -> dict:
    p=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-count_frames',
       '-show_entries','stream=width,height,r_frame_rate,nb_read_frames','-of','json',str(path)],
       capture_output=True,text=True,check=True)
    stream=json.loads(p.stdout)['streams'][0]
    return stream


def check_video(path: Path,frames: int,width: int,height: int):
    if not path.is_file():raise RuntimeError(f'Blender não gerou {path}')
    stream=media_probe(path)
    if int(stream.get('nb_read_frames',0))!=frames or stream.get('r_frame_rate')!='30/1':
        raise RuntimeError('Render da cena 05 não tem os 210 frames a 30 FPS exigidos')
    if [int(stream['width']),int(stream['height'])]!=[width,height]:
        raise RuntimeError('Render Blender da cena 05 com dimensões incorretas')


def main():
    a=argparse.ArgumentParser(description='MoneyPrint PDV scene05/Blender Quaternius CC0')
    a.add_argument('--characters-zip',type=Path)
    a.add_argument('--animations-zip',type=Path)
    a.add_argument('--quality',choices=('preview','final'),default='preview')
    a.add_argument('--no-checksum',action='store_true',help='Somente para versão Standard atualizada verificada manualmente')
    a.add_argument('--output-dir',type=Path,default=ROOT/'outputs')
    args=a.parse_args()
    dest=ROOT/'assets/quaternius'
    if bool(args.characters_zip)!=bool(args.animations_zip):a.error('Ambos os ZIPs Standard devem ser fornecidos juntos')
    if args.characters_zip:
        install_standard_zip(args.characters_zip,dest/'models',kind='characters',expected_sha256=None if args.no_checksum else STANDARD_BASE_SHA256)
        install_standard_zip(args.animations_zip,dest/'animations',kind='animations',expected_sha256=None if args.no_checksum else STANDARD_ANIM_SHA256)
    assets=find_standard_assets(dest)
    blender=shutil.which('blender')
    if not blender:raise RuntimeError('Blender 4.2+ GPL não encontrado no PATH; nenhum render criado')
    project=ROOT/'projects/pdv-artisys-quaternius-v1.json'
    data=json.loads(project.read_text(encoding='utf8'))
    scene=data['scenes'][4]
    if scene['id']!='05' or scene['duration_frames']!=210 or data['character_mode']!='quaternius_standard':
        raise RuntimeError('Contrato Quaternius inesperado')
    video=(ROOT/scene['video_texture']['file']).resolve()
    if not video.is_file():raise RuntimeError('Arquivo real do cardápio ausente: '+str(video))
    output=args.output_dir.resolve();output.mkdir(parents=True,exist_ok=True)
    build=HERE.parent/'build_blender.py'
    subprocess.run([blender,'-b','--factory-startup','--python',str(build),'--',
        '--project',str(project),'--scene','05','--quality',args.quality,
        '--output-dir',str(output),'--still','--animate'],check=True)
    blend=output/'pdv_artisys_scene_05.blend'
    image=output/'pdv_artisys_scene_05_still.png'
    movie=output/'pdv_artisys_scene_05.mp4'
    if not blend.is_file() or not image.is_file():raise RuntimeError('Arquivos .blend e/ou still ausentes')
    width,height=data['resolution'][args.quality]
    check_video(movie,210,width,height)
    report={'source':'Quaternius Standard CC0','model':assets['model'].name,
            'animation':assets['animation'].name,'matched_bones':assets['retarget']['compatible_bones'],
            'source_pdv_sha256':hashlib.sha256(video.read_bytes()).hexdigest(),
            'scene':'05','fps':30,'frames':210,'size':[width,height],
            'renders':{'blend':str(blend),'still':str(image),'mp4':str(movie)},
            'autopublish':False,'paid_services':False,'visual_qa':'manual_review_required'}
    (output/'pdv_artisys_scene_05_quaternius_qa.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print(json.dumps(report,indent=2,ensure_ascii=False))

if __name__=='__main__':main()
