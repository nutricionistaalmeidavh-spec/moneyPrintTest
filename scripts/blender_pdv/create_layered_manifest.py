"""Create canonical 12-scene Blender/MoneyPrint layer and source-media manifest."""
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import subprocess

HERE=Path(__file__).resolve()
ROOT=HERE.parents[2] if HERE.parent.name=='blender_pdv' else HERE.parents[1]
BASE=ROOT/'projects/pdv-artisys-quaternius-v1.json'
LAYER_IDS=['00_WORLD','10_RESTAURANT_SET','20_ACTORS_QUATERNIUS_CC0',
           '30_HAND_PROPS','40_DEVICES_3D','41_REAL_PDV_MOVIE_TEXTURES',
           '50_FLOATING_INFO','60_LIGHTS','70_CAMERA','90_SOURCE_ANIMATIONS_HIDDEN',
           '95_MONEYPRINT_TEXT_OVERLAYS','96_MONEYPRINT_SOUND']
CAPTIONS={
    '01':['Criei meu próprio sistema de PDV.','Do salão à cozinha.'],
    '02':['O problema','Ferramentas separadas atrasam o atendimento.'],
    '03':['A solução','Tudo em um só sistema.'],
    '04':['Operação no salão','Mesas, comandas e pedidos em tempo real.'],
    '05':['Cardápio digital','O cliente faz o pedido pelo celular.'],
    '06':['Garçom conectado','Pedidos e chamados em tempo real.'],
    '07':['Cozinha organizada','Da comanda ao KDS.'],
    '08':['Do pedido ao caixa','Pagamento sem retrabalho.'],
    '09':['Equipe e permissões','Cada pessoa com seu acesso.'],
    '10':['Estoque e cardápio','Ficha técnica, produtos e estoque conectados.'],
    '11':['Por trás do produto','Código, testes e evolução.'],
    '12':['Curtiu o projeto?','Segue e salva para ver os próximos sistemas.']
}
EXTRA={
 '01': [('assets/cliente-qr.mp4','phone',[2.15,-.8,1.48],4),
        ('assets/garcom.mp4','phone',[.12,-1.1,1.28],3)],
 '03': [('assets/mesas.mp4','tablet',[2.05,-.78,1.20],2)],
 '04': [('assets/gerar-qr.mp4','wall_panel',[1.4,2.65,3.42],1)],
 '06': [('assets/mesas.mp4','wall_panel',[1.15,2.6,3.55],3)],
 '07': [('assets/kds-sync.mp4','wall_panel',[1.1,2.72,3.36],4)],
 '08': [('assets/balcao.mp4','wall_panel',[1.2,2.75,3.6],5)],
 '10': [('assets/cardapio.mp4','wall_panel',[1.1,2.8,3.50],3)],
 '12': [('assets/cliente-qr.mp4','phone',[2.00,-.9,1.42],5),
        ('assets/garcom.mp4','phone',[.25,-1.1,1.22],4)]
}

def media_metadata(path):
    j=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams',
               '-show_format','-of','json',str(path)],text=True))
    v=next(s for s in j['streams'] if s['codec_type']=='video')
    return {'relative_path':str(path.relative_to(ROOT)),
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'bytes':path.stat().st_size,'dimensions':[v['width'],v['height']],
            'fps':v['r_frame_rate'],'duration_seconds':round(float(j['format']['duration']),3),
            'provenance':'Tutorial de operação PDV ArtiSys, Google Drive do proprietário',
            'redistribution':'Somente no pacote privado do proprietário'}

def build():
    project=json.loads(BASE.read_text(encoding='utf-8'))
    assets={str(p.relative_to(ROOT)):media_metadata(p) for p in sorted((ROOT/'assets').glob('*.mp4'))}
    project['extra_video_textures_schema']='blender-pdv-extra-screen-v1'
    project['renderer']='Blender 4.2+ bpy + FFmpeg, offline/selfhosted'
    project['use_pil_sprite_fallback']=False
    project['scene_collection_names']=LAYER_IDS
    for scene in project['scenes']:
        sid=scene['id'];n=scene['duration_frames']
        scene['extra_video_textures']=[
            {'file':path,'device':device,'position':pos,'offset_seconds':offset,'screen_material':'emissive_movie'}
            for path,device,pos,offset in EXTRA.get(sid,[])
        ]
        if sid=='07' and not any(a['role']=='garcom' for a in scene['actors']):
            actor=dict(scene['actors'][0]);actor['role']='garcom';actor['action']='deliver_plate'
            scene['actors'].append(actor)
        scene['editable_tracks']=[
            {'name':name,'enabled':name!='90_SOURCE_ANIMATIONS_HIDDEN',
             'kind':'scene_collection' if i<10 else 'post_composite_overlay'}
            for i,name in enumerate(LAYER_IDS)
        ]
        scene['typography']={'title':CAPTIONS[sid][0],
                             'accent':CAPTIONS[sid][1],
                             'color_title':'#F9F8FF','color_accent':'#A06AEF',
                             'editable':True,'animated_progressively_in_MoneyPrint':True}
        scene['assets_referenced']=(([scene['video_texture']['file']]
                        if scene.get('video_texture') else []) +
                           [x['file'] for x in scene.get('extra_video_textures',[])])
        for p in scene['assets_referenced']:
            if p not in assets:raise RuntimeError('Missing actual media '+p)
        scene['acting_timeline']=[
             {'role':a['role'],'action':a['action'],'start_frame':1,'end_frame':n,
              'action_source':'Quaternius Standard UAL base + manually authored bone keyframes'}
             for a in scene['actors']
        ]
    BASE.write_text(json.dumps(project,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    contract={
      'schema':'moneyprint-pdv-layered-3d-v1','project_file':'projects/pdv-artisys-quaternius-v1.json',
      'fps':30,'canvas':[1080,1920],'duration_seconds':82,
      'total_frames':2460,'scene_count':len(project['scenes']),
      'character_instances':sum(len(s['actors']) for s in project['scenes']),
      'screen_instances':sum(len(s['assets_referenced']) for s in project['scenes']),
      'collection_names':LAYER_IDS,
      'media_sources':assets,
      'scene_layers':[{ 'id':s['id'],'frames':s['duration_frames'],
                        'start_frame':s['start_frame'],'end_frame':s['end_frame'],
                        'character_actions':s['acting_timeline'],
                        'screen_mappings':s['assets_referenced'],
                        'layers':[t['name'] for t in s['editable_tracks']]} for s in project['scenes']],
      'render_status':'Blender not available in current runtime; editable source only',
      'license_quaternius':'CC0-1.0 Standard only',
      'requires': ['Blender 4.2+', 'Universal Base Characters [Standard]',
                   'Universal Animation Library [Standard]', 'FFmpeg'],
      'no_paid_dependencies':True,'autopublish':False
    }
    dst=ROOT/'timelines/scene_layers.json'
    dst.write_text(json.dumps(contract,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return contract

if __name__=='__main__':
    c=build()
    print('Scenes:',c['scene_count'],'Characters:',c['character_instances'],
          'Physical screen textures:',c['screen_instances'],'Real MP4:',len(c['media_sources']))
