"""Quaternius Standard CC0 import contract for Blender scene 05.

Core R$0, Python stdlib only for offline validation and archive installation.
No paid/Source/Pro fallback, no licenses silently bypassed. Real files are mandatory.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import struct
import zipfile
from pathlib import Path

BASE_URL = 'https://quaternius.itch.io/universal-base-characters'
ANIMATION_URL = 'https://quaternius.itch.io/universal-animation-library'
STANDARD_BASE_SHA256 = 'fdbf1804c90dfc1ea03e992bff7da2dfd1a79318e13270a660180f9308455f40'
STANDARD_ANIM_SHA256 = 'cc73fc4e495b82958207316596317a3f40b9fa38065bde1027937452da537724'

class AssetError(ValueError):
    pass


def inspect_model_gltf(path: Path) -> dict:
    path=Path(path)
    try:
        data=json.loads(path.read_text(encoding='utf8'))
        skins=data['skins']
        if not skins:raise KeyError('skins')
        joint_ids={n for sk in skins for n in sk['joints']}
        bone_names={data['nodes'][n]['name'] for n in joint_ids}
    except (KeyError, TypeError, IndexError, ValueError) as e:
        raise AssetError(f'Modelo glTF sem rig válido: {path}') from e
    return {'file':str(path),'bones':bone_names,'bone_count':len(bone_names)}


def inspect_animation_glb(path: Path) -> dict:
    path=Path(path)
    with path.open('rb') as f:
        head=f.read(20)
        if len(head)!=20:raise AssetError('GLB truncado')
        magic,version,total,chunk_size,chunk_type=struct.unpack('<IIIII',head)
        if magic!=0x46546C67 or version!=2 or chunk_type!=0x4E4F534A or not 0<chunk_size<20_000_000:
            raise AssetError(f'GLB inválido: {path}')
        if total>path.stat().st_size or chunk_size+20>total:raise AssetError('Cabeçalho GLB incoerente')
        try:data=json.loads(f.read(chunk_size).decode('utf8'))
        except (ValueError,UnicodeDecodeError) as e:raise AssetError('JSON GLB inválido') from e
    skins=data.get('skins') or []
    nodes=data.get('nodes') or []
    bones={nodes[i].get('name','') for skin in skins for i in skin.get('joints',[]) if 0<=i<len(nodes)}
    clips=[a.get('name','') for a in data.get('animations',[]) if a.get('name')]
    if not bones or not clips:raise AssetError('Biblioteca de animação sem rig ou clips válidos')
    return {'file':str(path),'bones':bones,'clips':clips,'bone_count':len(bones)}


def select_animation(available: list[str], preferences: list[str]) -> str:
    """Use a real clip by exact/substring name; never silently invent a motion."""
    for preference in preferences:
        exact=next((s for s in available if s.casefold()==preference.casefold()),None)
        if exact:return exact
        partial=next((s for s in available if preference.casefold() in s.casefold()),None)
        if partial:return partial
    raise AssetError('Nenhuma animação compatível da edição Standard: '+', '.join(preferences))


def normalize_bone(name: str) -> str:
    return re.sub(r'[^a-z0-9]','',name.lower().split(':')[-1])


def plan_retarget(source_bones: set[str], target_bones: set[str]) -> dict:
    shared=sorted({normalize_bone(n) for n in source_bones} & {normalize_bone(n) for n in target_bones})
    if len(shared)<max(5,min(len(source_bones),len(target_bones))*.60):
        raise AssetError(f'Rigs incompatíveis: somente {len(shared)} ossos correspondentes')
    return {'compatible_bones':len(shared),'matched':shared,'method':'normalized_bone_mapping'}


def find_standard_assets(folder: Path, *, female: bool=True) -> dict:
    folder=Path(folder)
    models=sorted(folder.rglob('*FullBody.gltf'))
    animations=sorted(folder.rglob('UAL1_Standard.glb'))
    if not models or not animations:
        raise AssetError('Precisamos dos pacotes gratuitos Standard em assets/quaternius; nunca usar personagem procedural de substituição')
    prefer=('Female' if female else 'Male')
    model=next((p for p in models if prefer in p.name and 'Regular' in p.name),None) or next((p for p in models if prefer in p.name),models[0])
    animation=animations[0]
    target=inspect_model_gltf(model)
    source=inspect_animation_glb(animation)
    return {'model':model,'animation':animation,'target_bones':target['bones'],'source_bones':source['bones'],
            'clips':source['clips'],'retarget':plan_retarget(source['bones'],target['bones'])}


def install_standard_zip(archive: Path, dest: Path, *,kind: str,expected_sha256: str|None=None) -> Path:
    """Install Standard-only archives with zip-slip and size controls."""
    archive=Path(archive);dest=Path(dest)
    if kind not in {'characters','animations'}:raise AssetError('Tipo de pacote inválido')
    name=archive.name.lower()
    if not name.endswith('.zip') or '[standard]' not in name or any(x in name for x in ('[pro]','[source]')):
        raise AssetError('Somente pacotes Quaternius [Standard] gratuitos')
    if expected_sha256:
        with archive.open('rb') as stream:
            digest=hashlib.file_digest(stream,'sha256').hexdigest()
        if digest!=expected_sha256:raise AssetError('SHA-256 divergente, download não confiável')
    with zipfile.ZipFile(archive) as z:
        files=z.infolist()
        if len(files)>4000 or sum(f.file_size for f in files)>2_000_000_000:raise AssetError('Arquivo excessivo')
        for f in files:
            p=Path(f.filename)
            if p.is_absolute() or '..' in p.parts or '\\' in f.filename or f.filename.startswith('/'):
                raise AssetError(f'Caminho inseguro no ZIP: {f.filename}')
        dest.mkdir(parents=True,exist_ok=True)
        z.extractall(dest)
    found=sorted(dest.rglob('UAL1_Standard.glb' if kind=='animations' else '*FullBody.gltf'))
    if not found:raise AssetError('Pacote Standard sem o arquivo solicitado')
    return found[0]


def main():
    p=argparse.ArgumentParser(description='Importe ZIPs Quaternius Standard gratuitos CC0; nunca Source/Pro')
    p.add_argument('--characters-zip',type=Path)
    p.add_argument('--animations-zip',type=Path)
    p.add_argument('--assets-dir',type=Path,default=Path('assets/quaternius'))
    p.add_argument('--no-checksum',action='store_true',help='Use só se você mesmo verificou outra versão Standard; mantém validação de formato')
    args=p.parse_args()
    if not args.characters_zip or not args.animations_zip:p.error('Ambos ZIPs Standard são obrigatórios')
    m=install_standard_zip(args.characters_zip,args.assets_dir/'models',kind='characters',
                           expected_sha256=None if args.no_checksum else STANDARD_BASE_SHA256)
    a=install_standard_zip(args.animations_zip,args.assets_dir/'animations',kind='animations',
                           expected_sha256=None if args.no_checksum else STANDARD_ANIM_SHA256)
    info=find_standard_assets(args.assets_dir)
    print(json.dumps({'model':str(m),'animation':str(a),'rig_match':info['retarget']['compatible_bones'],
                      'available_clips':info['clips'],'license':'CC0'},indent=2,ensure_ascii=False))

if __name__=='__main__':main()
