"""MoneyPrint Full300: five minute contextual Opus/Pillow editorial video.

25 canonical scenes, 9000 frames @30fps, Piper pt-BR, FFmpeg H.264.
The Opus MIT motion vocabulary is used contextually (no Remotion/Talkcraft).
Every software screenshot is captured from a real public GitHub README;
never invent or relabel a synthetic UI as authentic. No paid core provider.

Rendering is chunked per scene to allow recovery, QA and visible progress.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw

from scripts.pilot24_editor import (
    Stage, ease, font, ffprobe_duration, PAPER, VIOLET, BLUE, SAGE, RUST, INK, WHITE,
)
from scripts.opus_motion_adapter import motion_frame
from scripts.studio_render import build_plan

FPS=30
TOOL_REPOS={
    "erpnext":"https://github.com/frappe/erpnext",
    "twenty":"https://github.com/twentyhq/twenty",
    "chatwoot":"https://github.com/chatwoot/chatwoot",
    "plane":"https://github.com/makeplane/plane",
    "paperless":"https://github.com/paperless-ngx/paperless-ngx",
}
TOOL_NAMES={
    "erpnext":"ERPNext",
    "twenty":"Twenty",
    "chatwoot":"Chatwoot",
    "plane":"Plane",
    "paperless":"Paperless-ngx",
}
# Fixed semantic stage selection, preserving each of the canonical 25 voice cues.
FAMILY={
    1:"hook",2:"intro",3:"problem",4:"proof",5:"flow",6:"advice",
    7:"problem",8:"proof",9:"flow",10:"advice",
    11:"chat",12:"proof",13:"chat",14:"advice",
    15:"problem",16:"proof",17:"kanban",18:"advice",
    19:"problem",20:"proof",21:"flow",22:"advice",
    23:"recap",24:"advice",25:"outro",
}
SCENE_FAMILIES=set(FAMILY.values())
SCENE_TOOL={}
for tool,sequence in {
    "erpnext":range(3,7),"twenty":range(7,11),
    "chatwoot":range(11,15),"plane":range(15,19),
    "paperless":range(19,23),
}.items():
    for i in sequence: SCENE_TOOL[i]=tool

FLOW_LABELS={
    3:["PLANILHAS","CONFERÊNCIA","RETRABALHO","CUSTOS"],
    5:["PEDIDO","ESTOQUE","FINANCEIRO","CONTROLE"],
    7:["CONTATO","ORÇAMENTO","SEM RETORNO","PERDA"],
    9:["CONTATO","PROPOSTA","NEGOCIAÇÃO","FECHAMENTO"],
    11:["CANAIS","SEM HISTÓRICO","RESPOSTA DUPLA","ATRASO"],
    13:["MENSAGEM","ATRIBUIÇÃO","RESPOSTA","RESOLUÇÃO"],
    15:["REUNIÃO","TAREFAS","SEM PRAZO","ATRASO"],
    17:["A FAZER","EM EXECUÇÃO","CONCLUÍDO"],
    19:["DOCUMENTOS","PASTAS","BUSCA MANUAL","TEMPO"],
    21:["ENTRADA PDF","PROCESSAMENTO","METADADOS","PESQUISA"],
    23:["OPERAÇÃO","CLIENTES","ATENDIMENTO","PROJETOS","DOCUMENTOS"],
}
ADVICE={
    6:["SERVIDOR","CONFIGURAÇÃO","TREINAMENTO"],
    10:["HISTÓRICO","EQUIPE","ROTINA"],
    14:["CANAIS","REGRAS","CUSTOS EXTERNOS"],
    18:["PRIORIDADES","RESPONSÁVEIS","PROCESSO"],
    22:["ACESSO","BACKUP","ATUALIZAÇÕES"],
    24:["LICENÇA","HOSPEDAGEM","SEGURANÇA"],
}
SCREEN_LABELS={
    4:["VENDAS","COMPRAS","ESTOQUE","CONTABILIDADE"],
    8:["CONTATOS","EMPRESAS","OPORTUNIDADES"],
    12:["CONVERSAS","EQUIPE","ATENDIMENTO"],
    16:["TAREFAS","PROJETOS","ANDAMENTO"],
    20:["DOCUMENTOS","METADADOS","BUSCA"],
}
WARM=(246,238,219)
DARK=(20,31,48)

def scene_number(scene:dict)->int:
    return int(scene["id"].split("-")[-1])

def choose_direction(number:int)->str:
    return FAMILY[number]

def build_timeline(plan:dict)->list[dict]:
    if plan["fps"]!=FPS or plan["total_frames"]!=9000 or len(plan["scenes"])!=25:
        raise ValueError("O projeto inteiro deve ter 25 cenas e 9000 quadros a 30fps")
    out=[]
    for scene in plan["scenes"]:
        num=scene_number(scene)
        frames=scene["duration_frames"]
        out.append({"id":scene["id"],"start":scene["start_frame"],
                    "end":scene["end_frame"],"frames":frames,
                    "family":choose_direction(num),
                    "product":SCENE_TOOL.get(num),
                    "shot_count":max(3,math.ceil(frames/(FPS*3.3)))})
    if out[0]["start"]!=0 or out[-1]["end"]!=9000:
        raise ValueError("A timeline não cobre 5 minutos")
    for last,following in zip(out,out[1:]):
        if last["end"]!=following["start"]:
            raise ValueError("Lacuna entre cenas")
    return out

def source_assurance(assets,kind="app"):
    return kind in assets and isinstance(assets[kind],Image.Image)

def select_proof(captures,tool,kind="app"):
    value=captures.get(tool,{})
    return value.get(kind) if source_assurance(value,kind) else None

def _measure(text,length=28):
    words=str(text).split()
    result=[]
    line=""
    for word in words:
        maybe=(line+" "+word).strip()
        if len(maybe)>length and line:
            result.append(line)
            line=word
        else:
            line=maybe
    if line:result.append(line)
    return result

def _copy_stage(stage):
    return stage.im,stage.d

def _header(s,idx,title,subtitle=None,*,dark=False):
    fg=(240,236,224) if dark else INK
    accent=(160,140,212) if dark else VIOLET
    s.tx(112,93,f"{idx:02d}  /  MONEYPRINT",26,accent)
    for n,line in enumerate(_measure(title,27)[:2]):
        s.tx(105,157+105*n,line,70,fg)
    if subtitle:
        s.tx(109,368,str(subtitle)[:90],25,accent,False)

def _animated_type(s,words,local,top=520,*,max_size=116):
    for i,word in enumerate(words):
        p=ease((local-.19-i*.66)/.42)
        if p==0:continue
        y=top+i*99+(1-p)*85
        size=min(max_size,max(45,130-3*len(word)))
        s.tx(145,y,word,size,[VIOLET,INK,RUST,SAGE,BLUE][i%5])

def _flow(s,words,local,duration):
    # Preserves the causal pulse of vendored Opus cause-effect-chain;
    # contextual text differs by problem instead of reusing ERPNext labels.
    words=words[:5]
    n=len(words)
    cardw=370 if n<=4 else 295
    gap=(1740-n*cardw)/(n-1) if n>1 else 0
    y=600
    for k,label in enumerate(words):
        beat=(k+.18)*duration/(n+.55)
        p=ease((local-beat)/.50)
        if p<=0:continue
        x=100+k*(cardw+gap)
        s.box(x,y+(1-p)*95,cardw,248,WHITE,
              (177,165,153),22)
        s.box(x+17,y+23+(1-p)*95,57,57,
              [VIOLET,BLUE,SAGE,RUST][k%4],r=13)
        s.tx(x+35,y+30+(1-p)*95,str(k+1),31,WHITE)
        label=_measure(label,14)
        for j,line in enumerate(label[:2]):
            s.tx(x+27,y+110+j*53+(1-p)*95,line,36,INK)
        if k<n-1:
            progress=ease((local-beat-.4)/.7)
            if progress:
                xx=x+cardw+8
                dest=xx+gap-21
                s.line(xx,y+130,xx+(dest-xx)*progress,y+130,VIOLET,6)
                if progress>.9:s.tx(dest-5,y+95,">",39,VIOLET)
    # mild editorial underline, not a technical progress indicator
    if local>duration*.68:
        s.line(152,915,1760,915,SAGE,4)

def _chat(s,local,duration,idx):
    # Direct adaptation of the MIT chat-bubbles choreography:
    # staggered real-world explainer concepts, no synthetic app screenshot.
    texts=[
       "Quem ficou responsável?",
       "A conversa ficou sem resposta.",
       "Com histórico, a equipe se organiza.",
       "Atendimento concluído."
    ] if idx==11 else [
       "Nova conversa recebida",
       "Um agente assume",
       "Histórico disponível",
       "Resposta com contexto"
    ]
    for k,msg in enumerate(texts):
        beat=k*duration/5
        p=ease((local-beat)/.5)
        if p<=0:continue
        x=195 if k%2==0 else 710
        y=525+k*105+65*(1-p)
        w=1040 if k%2==0 else 940
        color=(235,229,248) if k%2==0 else (225,238,228)
        s.box(x,y,w,88,color,r=30)
        s.tx(x+37,y+24,msg,34,INK)
        if k==3:
            s.box(x+w-65,y+23,34,34,SAGE,r=17)
    s.tx(152,955,"CONTEXTO   /   RESPONSABILIDADE   /   RESPOSTA",
         22,VIOLET,False)

def _kanban(s,local,duration):
    width=515; lefts=[110,702,1294]; heads=["A FAZER","EM ANDAMENTO","CONCLUÍDO"]
    colors=[BLUE,VIOLET,SAGE]
    for i,(x,head) in enumerate(zip(lefts,heads)):
        s.box(x,520,width,400,(251,248,241),(202,198,193),24)
        s.box(x+20,538,width-40,67,colors[i],r=14)
        s.tx(x+41,549,head,33,WHITE)
    p=ease((local-.65)/3.2)
    card_x=130+(1190*p)
    card_y=676-80*math.sin(p*math.pi)
    s.box(card_x,card_y,472,145,(247,240,225),(188,175,155),20)
    s.tx(card_x+33,card_y+26,"ENTREGA DO PROJETO",31,INK)
    s.tx(card_x+35,card_y+86,"Responsável • Prazo",23,VIOLET,False)
    if local>duration*.55:
        s.tx(124,961,"QUANDO O CARD MUDA, O TRABALHO AVANÇA.",26,INK)

def _screenshot(s,source,local,rect,*,zoom=.035):
    # Pure editing over source image; no DOM fabrications or click animations.
    phase=(local%3.4)/3.4
    s.screenshot(source,rect,zoom=1+zoom*ease(phase),contain=True)

def _proof(s,tool,local,duration,captures,idx):
    repo=select_proof(captures,tool,"repo")
    app=select_proof(captures,tool,"app")
    variants=[x for x in [repo,app] if x is not None]
    if not variants:
        _animated_type(s,[TOOL_NAMES[tool],"CÓDIGO ABERTO"],local)
        return
    split=duration*.34
    # First screen: GitHub source, then actual app screenshot whenever available.
    phase=0 if local<split else 1 if local<duration*.68 else 2
    asset=(repo if phase==0 else (app or repo))
    if asset is None: asset=variants[0]
    s.box(95,420,1730,555,WHITE,r=32)
    z=.025+.05*(phase==2)
    _screenshot(s,asset,local,(126,445,1668,501),zoom=z)
    if phase==0:
        s.tx(123,976,TOOL_REPOS[tool].replace("https://",""),23,VIOLET,False)
    else:
        for j,label in enumerate(SCREEN_LABELS.get(idx,[])[:4]):
            if local>=split+j*.52:
                x=125+j*365
                s.box(x,934,338,73,(245,237,221),r=16)
                s.tx(x+24,951,label[:20],24,VIOLET)
    # Technical labels or names like "README screenshot" never appear on screen.

def _advice(s,idx,local,duration,captures):
    words=ADVICE[idx]
    tool=SCENE_TOOL.get(idx)
    app=select_proof(captures,tool,"app") if tool else None
    if app is not None and local>duration*.48:
        s.box(680,450,1130,510,WHITE,r=24)
        _screenshot(s,app,local,(700,470,1090,470))
        s.box(106,570,545,210,WHITE,r=18)
        s.tx(138,631,"PLANEJE ANTES",48,INK)
    else:
        for k,word in enumerate(words):
            p=ease((local-.25-k*duration*.24)/.5)
            if p<=0:continue
            x=135+k*556
            y=573+(1-p)*100
            s.box(x,y,493,245,WHITE,(211,202,189),25)
            s.box(x+24,y+28,68,63,[VIOLET,BLUE,SAGE][k],r=19)
            s.tx(x+48,y+37,str(k+1),31,WHITE)
            s.tx(x+33,y+128,word,37,INK)
    if idx==24 and local>duration*.65:
        s.tx(144,916,"OPEN SOURCE NÃO ELIMINA CUSTOS OPERACIONAIS.",27,RUST)

def _recap(s,local,captures):
    tools=list(TOOL_REPOS)
    current=min(4,int(local/2.8))
    tool=tools[current]
    selected=select_proof(captures,tool,"app") or select_proof(captures,tool,"repo")
    if selected is not None:
        s.box(654,417,1173,574,WHITE,r=29)
        _screenshot(s,selected,local,(680,440,1120,523),zoom=.065)
    s.tx(120,489,TOOL_NAMES[tool].upper(),74,VIOLET)
    words=["OPERAÇÕES","CLIENTES","ATENDIMENTO","PROJETOS","DOCUMENTOS"]
    s.tx(128,614,words[current],45,INK)
    for k in range(5):
        s.box(132+k*103,815,73,22,SAGE if k==current else (216,209,192),r=8)

def _outro(s,local,duration):
    names=list(TOOL_NAMES.values())
    for i,name in enumerate(names):
        p=ease((local-i*1.1)/.36)
        if p<=0:continue
        x=160+(i%2)*812
        y=545+(i//2)*128+(1-p)*52
        s.box(x,y,715,100,(251,248,240),(221,213,200),24)
        s.tx(x+33,y+22,name.upper(),45,INK)
    if local>duration*.53:
        s.tx(142,951,"LINKS DOS REPOSITÓRIOS NA DESCRIÇÃO",32,VIOLET)

def frame_scene(scene,local,captures,width=1920,height=1080):
    idx=scene_number(scene)
    duration=scene["duration_frames"]/FPS
    local=max(0,min(local,duration-1/FPS))
    family=choose_direction(idx)
    tool=SCENE_TOOL.get(idx)
    if idx==3:
        # Original Opus choreography in this dedicated 12s problem chapter.
        return motion_frame(local,width=width,height=height)
    s=Stage(width,height,local)
    dark=family in {"chat"}
    if dark:
        s.im.paste(DARK,(0,0,width,height))
        s.d=ImageDraw.Draw(s.im)
    _header(s,idx,scene["title"],TOOL_NAMES.get(tool) if tool else None,dark=dark)
    if family=="hook":
        _animated_type(s,["5 SISTEMAS","GRATUITOS","PARA EMPRESAS"],local,top=545,max_size=113)
    elif family=="intro":
        _animated_type(s,["GITHUB","É MAIS QUE CÓDIGO"],local,top=540,max_size=100)
        repo=select_proof(captures,"erpnext","repo")
        if repo is not None and local>6:
            s.box(720,530,1070,440,WHITE,r=24)
            _screenshot(s,repo,local,(738,548,1030,403))
    elif family=="problem":
        _flow(s,FLOW_LABELS[idx],local,duration)
    elif family=="proof":
        _proof(s,tool,local,duration,captures,idx)
    elif family=="flow":
        _flow(s,FLOW_LABELS[idx],local,duration)
        if idx==5 and local>duration*.65:
            # Actual ERPNext app only when captured; otherwise keep diagrams.
            image=select_proof(captures,"erpnext","app")
            if image is not None:
                s.box(915,460,881,500,WHITE,r=30)
                _screenshot(s,image,local,(935,480,840,460))
    elif family=="advice":
        _advice(s,idx,local,duration,captures)
    elif family=="chat":
        _chat(s,local,duration,idx)
    elif family=="kanban":
        _kanban(s,local,duration)
    elif family=="recap":
        _recap(s,local,captures)
    elif family=="outro":
        _outro(s,local,duration)
    else:
        raise ValueError(family)
    return s.im

def capture_all(output:Path):
    from scripts.repo_stills import capture_repo_stills
    output.mkdir(parents=True,exist_ok=True)
    captures={}
    diagnostics=[]
    for tool,url in TOOL_REPOS.items():
        dest=output/tool
        try:
            paths=capture_repo_stills([url],dest)[0]
            sources={Path(x).name:Path(x) for x in paths}
            mapping={}
            for role,name in [("repo","top.png"),("app","app_real.png")]:
                path=sources.get(name)
                if path and path.is_file():
                    with Image.open(path) as image:
                        mapping[role]=image.convert("RGB").copy()
            captures[tool]=mapping
            diagnostics.append({"software":tool,"repo":url,
                "captured":list(mapping),"images":{k:str(sources[v+".png"]) if False else str(sources.get("app_real.png" if k=="app" else "top.png")) for k in mapping}})
        except Exception as exc:
            captures[tool]={}
            diagnostics.append({"software":tool,"repo":url,"error":type(exc).__name__+": "+str(exc)[:250]})
    return captures,diagnostics

def create_voice(plan,model,output):
    """Per-scene Piper audio with exact duration, then continuous PCM narration."""
    if not Path(model).is_file():raise FileNotFoundError("Modelo Piper não encontrado")
    output.mkdir(parents=True,exist_ok=True)
    chunks=[]
    for index,scene in enumerate(plan["scenes"],1):
        raw=output/f"raw_{index:02d}.wav"
        subprocess.run(["piper","--model",str(model),"--output_file",str(raw)],
            input=scene["text"],text=True,capture_output=True,check=True)
        target=scene["duration_frames"]/FPS
        spoken=ffprobe_duration(raw)
        if not .1<spoken<180:
            raise RuntimeError(f"Narração inválida {scene['id']}")
        rate=max(.8,spoken/max(.1,target-.15))
        if rate>2.0:
            raise RuntimeError(f"Narração excede duração de {scene['id']}")
        out=output/f"voice_{index:02d}.wav"
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(raw),
            "-af",f"atempo={rate:.6f},apad,atrim=0:{target:.9f},aresample=48000",
            "-ar","48000","-ac","1","-c:a","pcm_s16le",str(out)],check=True)
        chunks.append(out)
        raw.unlink(missing_ok=True)
    playlist=output/"voice_concat.txt"
    playlist.write_text("\n".join("file '"+str(f.resolve())+"'" for f in chunks)+"\n",encoding="utf-8")
    merged=output/"narration.wav"
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat",
        "-safe","0","-i",str(playlist),"-ar","48000","-ac","1",
        "-c:a","pcm_s16le",str(merged)],check=True)
    if abs(ffprobe_duration(merged)-300)>.12:raise RuntimeError("A voz não cobre os 300s")
    return merged

def _render_scene(scene,captures,output,*,lowres=(960,540)):
    """Encode each canonical scene independently; concatenate on frame boundaries."""
    output.parent.mkdir(parents=True,exist_ok=True)
    fps=FPS; width,height=lowres
    cmd=["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
         "-f","rawvideo","-pixel_format","rgb24","-video_size",f"{width}x{height}",
         "-framerate",str(fps),"-i","pipe:0",
         "-vf","scale=1920:1080:flags=bicubic",
         "-c:v","libx264","-crf","23","-preset","veryfast","-threads","3",
         "-pix_fmt","yuv420p","-an","-movflags","+faststart",str(output)]
    process=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    try:
        for frame in range(scene["duration_frames"]):
            image=frame_scene(scene,frame/fps,captures,width,height)
            process.stdin.write(image.tobytes())
        process.stdin.close()
        if process.wait()!=0:raise RuntimeError("FFmpeg saiu com erro para "+scene["id"])
    finally:
        if process.poll() is None:process.kill()
    return output

def render_full(project,voice_model,output,*,smoke=False,smoke_scene=3):
    plan=build_plan(project)
    timeline=build_timeline(plan)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    capture_dir=output/"captures"
    captures,provenance=capture_all(capture_dir)
    (output/"fontes_reais.json").write_text(
        json.dumps(provenance,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if smoke:
        scene=plan["scenes"][smoke_scene-1]
        _render_scene(scene,captures,output/f"smoke_{smoke_scene:02d}.mp4",lowres=(640,360))
        return output/f"smoke_{smoke_scene:02d}.mp4"
    narration=create_voice(plan,voice_model,output/"audio")
    clips=[]
    for i,scene in enumerate(plan["scenes"],1):
        clip=output/"clips"/f"scene_{i:02d}.mp4"
        _render_scene(scene,captures,clip)
        clips.append(clip)
        print(f"CONCLUÍDA CENA {i:02d}/25: {scene['title']}",flush=True)
    playlist=output/"concat_video.txt"
    playlist.write_text("".join("file '"+str(p.resolve())+"'\n" for p in clips))
    video=output/"moneyprint_5min_opus.mp4"
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
        "-f","concat","-safe","0","-i",str(playlist),"-i",str(narration),
        "-map","0:v:0","-map","1:a:0",
        "-c:v","copy","-c:a","aac","-b:a","160k",
        "-t","300","-movflags","+faststart",str(video)],check=True)
    if abs(ffprobe_duration(video)-300)>.15:
        raise RuntimeError("Vídeo completo não tem exatamente 5 minutos")
    # 25 genuine mid-scene QA panels; no chart is treated as proof of app UI.
    sheet=Image.new("RGB",(1920,5*216),WARM)
    for i,scene in enumerate(plan["scenes"]):
        t=scene["duration_frames"]/FPS*.52
        thumbnail=frame_scene(scene,t,captures,384,216)
        sheet.paste(thumbnail,((i%5)*384,(i//5)*216))
    sheet.save(output/"qa_25_cenas.jpg",quality=85,optimize=True)
    details={"project":project["id"],"render":"full300-opus-ffmpeg",
             "fps":FPS,"width":1920,"height":1080,"frames":9000,
             "seconds":300,"scene_count":25,"programs":list(TOOL_REPOS),
             "motions":["breaking-news-takeover","cause-effect-chain",
                        "board-camera","chat-bubbles"],
             "license":"MIT adaptation, see vendor/opus-motion/LICENSE",
             "remotion_dependency":False,"talkcraft_dependency":False,
             "paid_api_dependency":False,"autopublish":False,
             "asset_source_report":"fontes_reais.json","scenes":timeline,
             "needs_human_visual_review":True}
    (output/"diagnostico_5min.json").write_text(
        json.dumps(details,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return video

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--project",required=True,type=Path)
    parser.add_argument("--voice-model",required=True,type=Path)
    parser.add_argument("--out",required=True,type=Path)
    parser.add_argument("--smoke",action="store_true")
    parser.add_argument("--smoke-scene",type=int,default=3)
    args=parser.parse_args()
    project=json.loads(args.project.read_text(encoding="utf-8"))
    result=render_full(project,args.voice_model,args.out,smoke=args.smoke,smoke_scene=args.smoke_scene)
    print("VÍDEO MONEYPRINT:",result,flush=True)

if __name__=="__main__":main()
