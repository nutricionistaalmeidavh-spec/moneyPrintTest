"""Executes Blender layered 3D scene building offline with explicit requirements.
The core never installs or bills cloud/commercial services.
"""
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve()
ROOT=HERE.parents[2] if HERE.parent.name=='blender_pdv' else HERE.parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--scene',default='05',help='01..12 or all')
    ap.add_argument('--quality',choices=('preview','final'),default='preview')
    ap.add_argument('--project',default='projects/pdv-artisys-quaternius-v1.json',help='JSON canônico; etapa 5 é um opt-in separado')
    ap.add_argument('--render-video',action='store_true')
    ap.add_argument('--render-passes',action='store_true')
    ap.add_argument('--posters',action='store_true')
    ap.add_argument('--out',default='output')
    opts=ap.parse_args()
    project_path=(ROOT/opts.project).resolve()
    if ROOT != project_path and ROOT not in project_path.parents:
        raise SystemExit('Caminho de projeto fora do workspace proibido')
    spec=json.loads(project_path.read_text(encoding='utf8'))
    if HERE.parent.name=='blender_pdv':
        from scripts.blender_pdv.build_blender import validate_plan
    else:
        from scripts.build_blender import validate_plan
    validate_plan(spec,ROOT,require_media=True)
    if HERE.parent.name=='blender_pdv':
        from scripts.blender_pdv.quaternius_assets import find_standard_assets
    else:
        from scripts.quaternius_assets import find_standard_assets
    find_standard_assets(ROOT/'assets/quaternius')
    blender=shutil.which('blender')
    if not blender:raise SystemExit('Blender 4.2+ não encontrado: .blend/MP4 não gerados')
    args=[blender,'-b','--factory-startup','--python',str(HERE.parent/'layered_scene.py'),'--',
          '--scene',opts.scene,'--project',str(project_path),
          '--quality',opts.quality,'--output-dir',str((ROOT/opts.out).resolve())]
    if opts.render_video:args.append('--render-video')
    if opts.render_passes:args.append('--render-passes')
    elif opts.posters:args.append('--layer-posters')
    subprocess.run(args,check=True)
    print('Blender executado; resultados em',ROOT/opts.out)

if __name__=='__main__':main()
