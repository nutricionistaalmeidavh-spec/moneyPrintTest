#!/usr/bin/env python3
"""Create a canonical Blender-ready 12-scene plan for MoneyPrint (stdlib only)."""
from __future__ import annotations
import json
from pathlib import Path

HERE=Path(__file__).resolve()
ROOT=HERE.parents[2] if HERE.parent.name=='blender_pdv' else HERE.parents[1]
FPS=30
ROLES=('desenvolvedor','garcom','cliente','cozinheiro','caixa','gerente')
SCENES=[
 ('01','Abertura',6,'full_3d','desenvolvedor','present','balcao.mp4','laptop','Apresentação do ecossistema PDV; começa com personagem e termina em notebook com tela real.'),
 ('02','O problema',7,'full_3d','garcom,cozinheiro,caixa','confused,waiting,check','', '', 'Garçom procura a comanda, cozinheiro espera, caixa tenta localizar pedido; atuações independentes, objetos desalinhados.'),
 ('03','A solução',7,'transition_3d','gerente,garcom','present,relief','balcao.mp4','laptop','Os personagens reorganizam a operação e a câmera termina na interface real.'),
 ('04','Operação no salão',6,'hybrid_3d','garcom,cliente','walk_point,scan','mesas.mp4','tablet','Garçom chega à mesa; cliente lê QR; mesa muda de status no material real.'),
 ('05','Cardápio digital',7,'full_3d','cliente','phone_tap','cliente-qr.mp4','phone','Cliente pega o celular e toca na tela; cardápio verdadeiro reproduzido no display.'),
 ('06','Garçom conectado',7,'hybrid_3d','garcom','notification','garcom.mp4','phone','Garçom recebe e confere o pedido, com toque e resposta facial.'),
 ('07','Cozinha e KDS',7,'full_3d','cozinheiro','cook','kds.mp4','monitor','Cozinheiro mexe no preparo, olha para o KDS real e confirma pedido pronto.'),
 ('08','Comanda e caixa',7,'hybrid_3d','caixa,cliente','checkout,relief','caixa.mp4','laptop','Operadora localiza a comanda e fecha a conta; cliente reage.'),
 ('09','Equipe e permissões',6,'hybrid_3d','gerente,garcom,caixa','assign_roles,nod,confirm','equipe.mp4','monitor','Gestor distribui perfis; visualização real do gerenciamento de acessos.'),
 ('10','Estoque e cardápio',7,'hybrid_3d','cozinheiro,gerente','cook,point','ficha.mp4','tablet','Cozinheiro monta prato, gestor confere ficha técnica real.'),
 ('11','Bastidores',6,'full_3d','desenvolvedor','type','relatorio.mp4','laptop','Dev digita, confere execução e ajusta produto; não divulgar repositório privado.'),
 ('12','Encerramento',9,'transition_3d','desenvolvedor,garcom,cliente','wave,nod,relief','balcao.mp4','laptop','Equipe e dispositivos convergem, foco na aplicação real, CTA sobreposto somente na montagem do MoneyPrint.')
]

def build():
    scenes=[];frame=0
    for id,title,duration,kind,roles,motions,video,device,description in SCENES:
        scene={'id':id,'title':title,'kind':kind,'start_frame':frame,'duration_frames':duration*FPS,
               'end_frame':frame+duration*FPS,'actors':[],
               'video_texture':None if not video else {'file':f'assets/{video}','device':device,
                    'offset_seconds': {'05':4,'06':3,'07':4,'08':4,'10':3}.get(id,2),
                    'clip_original':True},
               'direction':description,'composition':{'render':'blender','text_overlay':'MoneyPrint','audio':'MoneyPrint'},
               'camera':{'type':'orthographic','move':'dolly_in' if id not in ('02','09') else 'orbit_subtle'},
               'background':'restaurant' if id not in ('11','01') else 'software_studio'}
        for role,motion in zip(roles.split(','),motions.split(',')):
            scene['actors'].append({'id':f'{id}-{role}','role':role,'action':motion,
                      'animation':{'start_frame':8,'end_frame':duration*FPS-9,
                                   'head_turn_degrees':12,'arm_gesture_degrees':36},
                      'render_asset':'rigged_character'})
        scenes.append(scene);frame+=duration*FPS
    return {'schema_version':1,'project':'pdv-artisys-blender-v1','fps':FPS,'aspect':'9:16',
            'resolution':{'preview':[540,960],'final':[1080,1920]},'total_frames':frame,
            'duration_seconds':frame/FPS,'autopublish':False,'no_paid_dependencies':True,
            'character_mode':'procedural_preview',
            'character_quality_note':'Rig 3D procedural é protótipo técnico, não arte final. Para produção substituir pelos modelos CC0 rigged por personagem com licença verificada.',
            'assets_policy':{'real_pdv_footage':'local original from Drive',
                             'external_characters':'optional verified CC0 (explicit import)',
                             'paid_services':'none'},
            'character_library':[{'id':r,'preferred_source':'Quaternius Universal Base Characters + Universal Animation Library',
                'license':'CC0 (check each asset version)'} for r in ROLES],
            'prop_library':['laptop','tablet','phone','monitor_KDS','balcao','mesa','cadeira','prato','QR_code','comanda','luminaria','plantas'],
            'scenes':scenes}

if __name__=='__main__':
    d=build();path=ROOT/'projects'/'pdv-artisys-blender-v1.json';path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
    print(f'{path} / {len(d["scenes"])} cenas / {d["total_frames"]} frames')
