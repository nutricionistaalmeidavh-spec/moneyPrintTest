"""MoneyPrint dialogue voice production using self-hosted Paradee-8M Pt-BR.
Audio is rendered in a separate step; no cloud TTS/API keys needed.
MIT? Script is bespoke, models retain Apache 2.0.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

SCENES = [
    {"key":"01_abertura","label":"SISTEMAS CAROS?", "seconds":9.0,"lines":[
      ("A","Mano, tô abrindo meu restaurante e tô ficando maluco! Todo sistema que eu encontro tem mensalidade. Não tem outra saída?"),
      ("B","Tem, cara! Tá pagando caro em sistemas? Olha isso aqui!"),]},
    {"key":"02_restaurante","label":"FLOCAFE · PDV", "seconds":18.0,"lines":[
      ("A","Mas eu preciso controlar mesa, pedido, caixa... Dá pra fazer isso sem assinatura?"),
      ("B","Dá! Conhece o FloCafe? É um PDV open source que roda no seu computador. Você cadastra produtos, organiza mesas, lança pedidos e manda tudo pra cozinha!"),
      ("A","Até o pedido do garçom?"),
      ("B","Isso! E depois você fecha a conta no caixa."),]},
    {"key":"03_crm","label":"TWENTY · CRM", "seconds":13.0,"lines":[
      ("A","Tá, mas e os clientes? Eu vivo perdendo contato e orçamento!"),
      ("B","Aí você usa o Twenty CRM! Cadastra os clientes e acompanha cada negociação até fechar a venda."),]},
    {"key":"04_documentos","label":"PAPERLESS-NGX · DOCUMENTOS", "seconds":13.0,"lines":[
      ("A","E os contratos, notas e documentos? Tá tudo uma bagunça!"),
      ("B","Paperless-ngx! Você digitaliza os documentos, organiza tudo e encontra arquivos até pesquisando pelo conteúdo."),]},
    {"key":"05_projetos","label":"OPENPROJECT · PROJETOS", "seconds":13.0,"lines":[
      ("A","E pra organizar a equipe? Ninguém sabe o que tem que entregar!"),
      ("B","OpenProject! Você organiza projetos, define responsáveis, acompanha tarefas e controla os prazos."),]},
    {"key":"06_descoberta","label":"OPEN SOURCE · SEM ASSINATURA", "seconds":11.0,"lines":[
      ("A","Pera aí... E esses sistemas são gratuitos mesmo?"),
      ("B","São projetos de código aberto, com opções gratuitas pra instalar por conta própria. Só lembra que hospedagem, equipamentos ou recursos extras podem ter custos."),]},
    {"key":"07_cta","label":"SIGA A ARTISYS", "seconds":8.0,"lines":[
      ("A","Caramba! Onde eu encontro esses negócios?"),
      ("B","No GitHub! E segue a ArtiSys pra conhecer mais sistemas que podem facilitar sua vida!"),]},
]

def make_plan(scenes=SCENES):
    result=[]; cursor=0.0
    for scene in scenes:
        assert scene['seconds']>0
        assert scene['key'] not in [p['key'] for p in result]
        lines=[{'speaker':who,'text':txt} for who,txt in scene['lines']]
        assert all(x['speaker'] in ['A','B'] and x['text'] for x in lines)
        result.append({'key':scene['key'],'label':scene['label'],'nominal_seconds':scene['seconds'],'start':round(cursor,3),'end':round(cursor+scene['seconds'],3),'lines':lines})
        cursor+=scene['seconds']
    return result

def split_for_tts(text,max_len=160):
    # Break at sentence punctuation to keep ONNX G2P input under 512 tokens.
    pieces=re.split(r'(?<=[.!?])\s+',text.strip()); result=[];cur=''
    for p in pieces:
        if len(p)>max_len:
            words=p.split()
            for word in words:
                if len(cur+' '+word)>max_len and cur:
                    result.append(cur.strip());cur=''
                cur+=((' ' if cur else '')+word)
        elif len(cur)+len(p)+1<=max_len:
            cur+=((' ' if cur else '')+p)
        else:
            if cur:result.append(cur)
            cur=p
    if cur:result.append(cur)
    assert all(1<=len(x)<=max_len for x in result)
    return result

def synthesize(out:Path,model_dir:Path):
    import numpy as np
    import soundfile as sf
    import onnxruntime as ort
    from misaki.espeak import EspeakG2P
    out.mkdir(parents=True,exist_ok=True)
    vocab=json.loads((model_dir/'config.json').read_text())['vocab']
    sess=ort.InferenceSession(str(model_dir/'onnx'/'paradee_alex_int8.onnx'),providers=['CPUExecutionProvider'])
    g2p=EspeakG2P(language='pt-br')
    sr=24000
    actual=[];all_audio=[];cur=0
    def append(arr):
        nonlocal cur
        arr=np.asarray(arr,dtype=np.float32).reshape(-1)
        all_audio.append(arr)
        cur+=len(arr)
    def silence(sec):append(np.zeros(int(sr*sec),dtype=np.float32))
    for scene in make_plan():
        scene_start=cur/sr; lines=[]
        per_line_nominal=scene['nominal_seconds']/len(scene['lines'])
        for line in scene['lines']:
            speaker=line['speaker']
            silence(.14 if speaker=='A' else .20)
            start=cur/sr
            chunks=[]
            for phrase in split_for_tts(line['text'],115):
                phonemes,_=g2p(phrase)
                tokens=[0]+[vocab[c] for c in phonemes if c in vocab][:510]+[0]
                ids=np.array([tokens],dtype=np.int64)
                speed=np.array([1.15 if speaker=='A' else 1.21],dtype=np.float32)
                wave=sess.run(None,{'input_ids':ids,'speed':speed})[0][0]
                chunks.extend([np.asarray(wave,dtype=np.float32),np.zeros(int(.065*sr),dtype=np.float32)])
            wave=np.concatenate(chunks)
            # Audible distinction without changing same model: dialogue B uses small pitch shift postprocess later.
            append(wave)
            end=cur/sr
            lines.append({'speaker':speaker,'text':line['text'],'start':round(start,3),'end':round(end,3),'duration':round(end-start,3)})
        # Never truncate speech, add breathing room before next scene.
        used=cur/sr-scene_start
        silence(max(.27,scene['nominal_seconds']-used))
        actual.append({'key':scene['key'],'label':scene['label'],'start':round(scene_start,3),'end':round(cur/sr,3),'seconds':round(cur/sr-scene_start,3),'nominal_seconds':scene['nominal_seconds'],'lines':lines})
        print(scene['key'],round(scene_start,2),round(cur/sr,2),'real sec',round(used,2),flush=True)
    wave=np.concatenate(all_audio)
    sf.write(out/'dialogo_narracao.wav',wave,sr)
    (out/'speech_cues.json').write_text(json.dumps({'source':'Paradee-8M-PtBr Alex int8 (Apache-2.0), local ONNX inference','scenes':actual,'total_seconds':round(cur/sr,3)},ensure_ascii=False,indent=2))
    return actual

if __name__=='__main__':
    if '--plan-only' in sys.argv:
        print(json.dumps(make_plan(),ensure_ascii=False,indent=2))
    else:
        synthesize(Path(sys.argv[1]),Path(sys.argv[2]))