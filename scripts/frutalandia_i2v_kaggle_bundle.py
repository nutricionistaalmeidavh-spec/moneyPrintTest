"""Build a self-contained PRIVATE Kaggle GPU kernel for true LTX image-to-video.

Bundled assets are original user-approved character reference + story + I2V code.
No credentials or external image hosts are included in the kernel payload.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import re
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SLUG=re.compile(r"^[a-z0-9][a-z0-9_-]{1,39}$")
SCENES=tuple(f"s{i:02d}" for i in range(1,7))


def build_kaggle_kernel(output_dir: Path, username: str, scene_id: str = "s01",
                       slug: str = "frutalandia-i2v-s01") -> Path:
    if not SLUG.fullmatch(username) or not SLUG.fullmatch(slug):
        raise ValueError("Kaggle username ou kernel slug inválido")
    if scene_id not in SCENES:
        raise ValueError("ID de cena fora de s01..s06")
    outputs=Path(output_dir)
    outputs.mkdir(parents=True,exist_ok=True)
    files=(
        "assets/frutalandia/elenco-master.webp",
        "assets/frutalandia/elenco-reference.webp",
        "assets/frutalandia/reference-manifest.json",
        "stories/frutalandia/contador-do-butico-ep01.json",
        "scripts/frutalandia_i2v.py",
    )
    payload=io.BytesIO()
    with zipfile.ZipFile(payload,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name in files:
            z.write(ROOT/name,name)
        z.writestr("scripts/__init__.py","")
    b64=base64.b64encode(payload.getvalue()).decode("ascii")
    # Fast preflight: do not update apt repositories in Kaggle. Abort visibly if
    # Kaggle has no GPU or network for public model weights/dependencies.
    script=(
        "import base64, io, json, os, pathlib, shutil, socket, subprocess, sys, zipfile\n"
        "from pathlib import Path\n"
        "print('FRUTALANDIA_I2V_STAGE=started',flush=True)\n"
        "root=Path('/kaggle/working/frutalandia-i2v-project')\n"
        "root.mkdir(parents=True,exist_ok=True)\n"
        f"bundle={b64!r}\n"
        "with zipfile.ZipFile(io.BytesIO(base64.b64decode(bundle))) as z:\n"
        "    z.extractall(root)\n"
        "os.chdir(root)\n"
        "sys.path.insert(0,str(root))\n"
        "out=Path('/kaggle/working')\n"
        "print('FRUTALANDIA_I2V_STAGE=reference_unpacked',flush=True)\n"
        "if not shutil.which('nvidia-smi'):\n"
        "    raise RuntimeError('KAGGLE_GPU_UNAVAILABLE: Accelerator None; parar antes de baixar pesos')\n"
        "p=subprocess.run(['nvidia-smi','-L'],capture_output=True,text=True,timeout=12)\n"
        "print('FRUTALANDIA_GPU_CHECK:',p.stdout.strip()[:250],flush=True)\n"
        "if p.returncode or 'GPU' not in p.stdout:\n"
        "    raise RuntimeError('KAGGLE_GPU_UNAVAILABLE: GPU não alocada pelo Kaggle')\n"
        "try:\n"
        "    socket.setdefaulttimeout(12)\n"
        "    socket.getaddrinfo('huggingface.co',443)\n"
        "except OSError as e:\n"
        "    raise RuntimeError('FRUTALANDIA_NETWORK_PREFLIGHT_FAIL: internet/DNS Kaggle indisponível; não tentar apt/pip') from e\n"
        "print('FRUTALANDIA_NETWORK_PREFLIGHT=ok',flush=True)\n"
        "print('FRUTALANDIA_I2V_STAGE=python_dependencies',flush=True)\n"
        "p=subprocess.run([sys.executable,'-m','pip','install','-q','--disable-pip-version-check',\n"
        "    '--retries','1','--timeout','15',\n"
        "    'diffusers>=0.35,<1','transformers>=4.48,<5',\n"
        "    'accelerate>=1,<2','safetensors>=0.4','imageio-ffmpeg>=0.5',\n"
        "    'av>=14','pillow>=10,<13'],timeout=350)\n"
        "if p.returncode:\n"
        "    raise RuntimeError('DEPENDENCIES_FAILED: Kaggle pip indisponível ou incompatível')\n"
        "import torch\n"
        "from scripts.frutalandia_i2v import check_available_gpu,load_story,prepare_reference,get_scene_prompt,run_model,validate_preview\n"
        "check_available_gpu(torch)\n"
        "story=load_story(root/'stories/frutalandia/contador-do-butico-ep01.json')\n"
        "prepare_reference(story,out/'first-frames')\n"
        "print('FRUTALANDIA_I2V_STAGE=weights_loading',flush=True)\n"
        f"scene_id={scene_id!r}\n"
        "clip=out/('preview-'+scene_id+'.mp4')\n"
        "run_model(out/'first-frames'/('first-frame-'+scene_id+'.png'),\n"
        "    get_scene_prompt(story,scene_id),clip,2,steps=28,seed=42)\n"
        "qa=validate_preview(clip,2)\n"
        "record={'status':'REAL_VIDEO_VALIDATED','scene':scene_id,'file':clip.name,\n"
        "    'qa':qa,'auto_publish':False,'paid_provider':False}\n"
        "(out/'frutalandia-i2v-result.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))\n"
        "print('FRUTALANDIA_I2V_STAGE=complete',json.dumps(record,ensure_ascii=False),flush=True)\n"
    )
    (outputs/"run.py").write_text(script,encoding="utf-8")
    metadata={
        "id":f"{username}/{slug}",
        "title":slug.replace("-"," ").title(),
        "code_file":"run.py",
        "language":"python",
        "kernel_type":"script",
        "is_private":True,
        "enable_gpu":True,
        "enable_internet":True,
        "machine_shape":"NvidiaTeslaT4",
        "dataset_sources":[],
        "competition_sources":[],
        "kernel_sources":[],
        "model_sources":[],
    }
    (outputs/"kernel-metadata.json").write_text(
        json.dumps(metadata,indent=2)+"\n",encoding="utf-8"
    )
    return outputs/"run.py"


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,default=Path(".kaggle-frutalandia-i2v"))
    parser.add_argument("--username",required=True)
    parser.add_argument("--scene-id",default="s01",choices=SCENES)
    parser.add_argument("--slug",default="frutalandia-i2v-s01")
    args=parser.parse_args()
    script=build_kaggle_kernel(args.out,args.username.lower(),args.scene_id,args.slug)
    print("PRIVATE_KAGGLE_I2V_KERNEL_PREPARED",script)

if __name__=="__main__":
    main()
