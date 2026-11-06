"""Carrossel TikTok com FOTOS REAIS do Pixabay via secret do GitHub.

Não gera imagens por IA e não desfoca/faz caixas atrás dos textos.
O catálogo de candidatos e a licença da imagem escolhida acompanham a entrega.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import zipfile
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from PIL import Image, ImageDraw, ImageFont, ImageOps

API_ENDPOINT = "https://pixabay.com/api/"
W, H = 1080, 1920
AGENT = "MoneyPrintTest/1.0 (Pixabay photos for a user-directed TikTok carousel)"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MED = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


class CarouselError(RuntimeError):
    pass


def validate_job(raw: dict) -> dict:
    if not isinstance(raw, dict) or (set(raw) - {"topic", "searches", "texts", "photo_id", "handle"}):
        raise ValueError("Pedido inválido ou com campos não permitidos")
    topic = raw.get("topic", "")
    if not isinstance(topic, str) or not (3 <= len(topic) <= 140):
        raise ValueError("Tema inválido")
    searches = raw.get("searches")
    if (not isinstance(searches, list) or not 1 <= len(searches) <= 6 or
        any(not isinstance(x,str) or not 3 <= len(x) <= 70 or
            any(ch in x for ch in "\r\n\x00") for x in searches)):
        raise ValueError("Forneça até 6 termos curtos de busca")
    texts = raw.get("texts")
    if (not isinstance(texts,list) or len(texts)!=5 or
        any(not isinstance(x,str) or not (5 <= len(x.strip()) <= 220) or
            "\x00" in x for x in texts)):
        raise ValueError("São exigidos 5 textos")
    pid = raw.get("photo_id")
    if pid is not None and (type(pid) is not int or pid <= 0):
        raise ValueError("photo_id inválido")
    handle = raw.get("handle", "@debora.lactacao")
    if not isinstance(handle,str) or not re.fullmatch(r"@[A-Za-z0-9._]{3,40}", handle):
        raise ValueError("Identificação de perfil inválida")
    return {"topic": topic.strip(), "searches":searches,
            "texts":[t.strip() for t in texts], "photo_id":pid, "handle":handle}


def safe_photo_url(url: str) -> bool:
    try:
        p = urlsplit(url)
        return (p.scheme=="https" and
                ((p.hostname=="cdn.pixabay.com" and
                  p.path.lower().endswith((".jpg",".jpeg",".png",".webp"))) or
                 (p.hostname=="pixabay.com" and p.path.startswith("/get/"))))
    except (TypeError, ValueError):
        return False


def source_photo_url(hit: dict) -> str:
    for key in ("largeImageURL", "webformatURL"):
        url = hit.get(key)
        if isinstance(url,str) and safe_photo_url(url):
            return url
    raise CarouselError("Foto do Pixabay sem URL de mídia permitido")


def score_hit(hit: dict) -> float:
    tags = str(hit.get("tags","")).lower()
    w,h=hit.get("imageWidth",0),hit.get("imageHeight",0)
    if (not isinstance(w,int) or not isinstance(h,int) or w<800 or h<800
        or not hit.get("id")):
        return -10000.0
    if not any(s in tags for s in ("baby","breast","nursing","pump","milk","mother","lactation","bottle","newborn")):
        return -10000.0
    score=0
    phrases=[("breast milk",26),("breastmilk",26),("breastfeeding",18),
             ("breast pump",25),("expressed",12),("lactation",16),
             ("newborn",8),("mother",5),("baby",7),("bottle",10),
             ("milk",2),("nursing",9),("hands",4),("close up",6),
             ("pump",12),("family",2)]
    for s,v in phrases:
        if s in tags:score+=v
    for negative in ("cow","cattle","farm","goat","coffee","cheese","dairy farm",
                     "dog","cat","drink","latte","breast cancer","alcohol",
                     "illustration","drawing","vector"):
        if negative in tags:score-=40
    if h>w: score+=12
    elif w/h>2:score-=15
    if h>=1400 and w>=1000:score+=3
    return score


def select_candidates(hits: list[dict]) -> list[dict]:
    by_id={}
    for hit in hits:
        try:
            source_photo_url(hit)
            score=score_hit(hit)
            if score>=12 and (hit.get("id") not in by_id or score>score_hit(by_id[hit["id"]])):
                by_id[hit["id"]]=hit
        except (CarouselError, KeyError, TypeError):
            continue
    return sorted(by_id.values(),key=lambda x: (score_hit(x),int(x.get("views",0))),reverse=True)


def fetch_candidates(secret: str, searches: list[str]) -> list[dict]:
    if not secret:
        raise CarouselError("PIXABAY_API_KEY não está configurada no GitHub Actions")
    results=[]
    for term in searches:
        q=urlencode({"key":secret, "q":term, "image_type":"photo",
                     "per_page":50,"safesearch":"true","order":"popular"})
        request=Request(API_ENDPOINT+"?"+q,headers={"User-Agent":AGENT})
        try:
            with urlopen(request, timeout=30) as response:
                payload=json.load(response)
            if not isinstance(payload.get("hits"),list):
                raise ValueError("Resposta sem hits")
            results.extend(payload["hits"])
        except Exception as exc:
            # NÃO incluir exception ou URL, pois incluem a secret como query string.
            raise CarouselError("Pixabay recusou a consulta ou não respondeu; confira a secret e permissões") from None
    picked=select_candidates(results)
    print(f"Pixabay: {len(results)} fotos retornadas; {len(picked)} candidatas relevantes.", flush=True)
    if not picked:
        hosts=sorted(set(urlsplit(str(z.get("webformatURL",""))).hostname or "" for z in results))[:5]
        print(f"Pixabay: domínios dos resultados {hosts}.", flush=True)
        print(f"Pixabay: primeiras tags {[str(z.get('tags',''))[:90] for z in results[:5]]}.", flush=True)
    return picked


def get_photo(url: str) -> Image.Image:
    if not safe_photo_url(url):
        raise CarouselError("Fonte de foto não permitida")
    request=Request(url,headers={"User-Agent":AGENT})
    try:
        with urlopen(request,timeout=65) as response:
            if not safe_photo_url(response.geturl()):
                raise CarouselError("Redirecionamento proibido")
            size=0
            bio=io.BytesIO()
            while data:=response.read(1024*1024):
                size+=len(data)
                if size>17*1024*1024:
                    raise CarouselError("Fotografia muito grande")
                bio.write(data)
        bio.seek(0)
        image=Image.open(bio)
        image.load()
        if image.width<750 or image.height<750:
            raise CarouselError("Foto com resolução insuficiente")
        return ImageOps.exif_transpose(image).convert("RGB")
    except CarouselError:
        raise
    except Exception:
        raise CarouselError("Não foi possível obter uma fotografia do Pixabay") from None


def build_text_lines(draw: ImageDraw.ImageDraw, text: str, ft, maxwidth: int):
    lines=[]
    line=""
    for token in text.split():
        trial=(line+" "+token).strip()
        if draw.textbbox((0,0),trial,font=ft)[2]>maxwidth and line:
            lines.append(line)
            line=token
        else:
            line=trial
    if line:lines.append(line)
    return lines


def fit_text(draw: ImageDraw.ImageDraw,text: str,maxwidth=940,maxheight=920):
    for size in range(104,43,-2):
        ft=ImageFont.truetype(FONT_BOLD,size)
        lines=build_text_lines(draw,text,ft,maxwidth)
        height=len(lines)*int(size*1.26)
        if height<maxheight and all(draw.textbbox((0,0),line,font=ft)[2]<=maxwidth for line in lines):
            return ft,lines
    raise CarouselError("Texto excessivamente longo")


def render_slides(src: Path, output: Path, job: dict) -> list[Path]:
    """No photo blur, shade, box, panel or image mutation behind titles."""
    output.mkdir(parents=True,exist_ok=True)
    original=Image.open(src).convert("RGB")
    # Cobre quadro por crop, sem blur nem overlay que esconda a fotografia.
    photo=ImageOps.fit(original,(W,H),Image.Resampling.LANCZOS,centering=(.5,.45))
    saved=[]
    for idx,content in enumerate(job["texts"],start=1):
        canvas=photo.copy()
        draw=ImageDraw.Draw(canvas)
        ft,lines=fit_text(draw,content)
        step=int(ft.size*1.26)
        blockheight=len(lines)*step
        y=max(340,int(H*.51-blockheight/2))
        # Branco é SOMENTE contorno de letra; foto continua nítida.
        for line in lines:
            box=draw.textbbox((0,0),line,font=ft)
            x=max(55,(W-(box[2]-box[0]))//2)
            draw.text((x,y),line,font=ft,fill=(18,17,19),
                      stroke_width=8,stroke_fill=(255,255,255))
            y+=step
        f_small=ImageFont.truetype(FONT_BOLD,33)
        draw.text((65,160),job["handle"],font=f_small,fill=(255,255,255),
                  stroke_width=3,stroke_fill=(20,20,20))
        count=f"{idx:02d}/05"
        width=draw.textbbox((0,0),count,font=f_small)[2]
        draw.text((W-64-width,160),count,font=f_small,fill=(255,255,255),
                  stroke_width=3,stroke_fill=(20,20,20))
        file=output/f"{idx:02d}_debora_tiktok.png"
        canvas.save(file,format="PNG",optimize=True)
        saved.append(file)
    return saved


def make_gallery(candidates: list[dict], folder: Path):
    thumbs=[]
    f=ImageFont.truetype(FONT_BOLD,23)
    for candidate in candidates[:8]:
        try:
            img=get_photo(source_photo_url(candidate))
        except CarouselError:
            continue
        thumb=ImageOps.fit(img,(280,400),Image.Resampling.LANCZOS)
        d=ImageDraw.Draw(thumb)
        # Essa etiqueta aparece APENAS na galeria de curadoria, não nos slides.
        d.rectangle((0,355,280,400),fill=(255,255,255))
        d.text((10,365),f"Pixabay #{candidate['id']}",font=f,fill=(30,30,30))
        thumbs.append(thumb)
    if thumbs:
        cols=4
        rows=(len(thumbs)+cols-1)//cols
        contact=Image.new("RGB",(280*cols,400*rows),(243,243,243))
        for i,thumb in enumerate(thumbs):
            contact.paste(thumb,((i%cols)*280,(i//cols)*400))
        contact.save(folder/"curadoria_pixabay.jpg",quality=90)


def build_carousel(jobfile: Path, output: Path):
    job=validate_job(json.loads(jobfile.read_text(encoding="utf-8")))
    secret=os.environ.get("PIXABAY_API_KEY","").strip()
    candidates=fetch_candidates(secret,job["searches"])
    if not candidates:
        raise CarouselError("Pixabay não encontrou fotografias reais relevantes; nenhuma imagem gerada foi substituída silenciosamente")
    output.mkdir(parents=True,exist_ok=True)
    (output/"candidatas.json").write_text(json.dumps([
        {"id":c["id"],"score":score_hit(c),"tags":c["tags"],
         "pageURL":c.get("pageURL"),"user":c.get("user")} for c in candidates[:20]
    ],ensure_ascii=False,indent=2),encoding="utf-8")
    make_gallery(candidates,output)
    preferred=[c for c in candidates if c["id"]==job["photo_id"]] if job["photo_id"] else candidates
    selected=None
    for hit in preferred:
        try:
            photo=get_photo(source_photo_url(hit))
            selected=hit
            break
        except CarouselError:
            continue
    if selected is None:
        raise CarouselError("Não foi possível baixar uma foto real adequada do Pixabay")
    source_path=output/"fotografia_original_pixabay.jpg"
    photo.save(source_path,quality=94)
    slides=render_slides(source_path,output,job)
    metadata={
        "topic":job["topic"],"photo_id":selected["id"],
        "photographer":selected.get("user",""),"source":selected.get("pageURL",""),
        "license":"Pixabay Content License — confira restrições de marcas/pessoas no material",
        "tags":selected.get("tags",""),
        "source_type":"fotografia REAL pesquisada via PIXABAY_API_KEY",
        "slide_count":len(slides),"size":[W,H],"photo_blur":False,
        "file_names":[x.name for x in slides],
    }
    (output/"origem_e_licenca.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding="utf-8")
    msg=("Peito mais macio não significa, necessariamente, pouco leite! "
         "A produção pode se ajustar às necessidades do bebê. "
         "Para avaliar se ele recebe leite suficiente, acompanhe as mamadas, "
         "as fraldas molhadas e o ganho de peso. Em caso de dúvidas, busque "
         "uma avaliação individualizada.\n\n@debora.lactacao\n"
         "#Amamentacao #LeiteMaterno #Lactacao #Maternidade")
    (output/"legenda_tiktok.txt").write_text(msg,encoding="utf-8")
    preview=Image.new("RGB",(300*5,534),"white")
    for idx,slide in enumerate(slides):
        preview.paste(Image.open(slide).resize((300,534)),(idx*300,0))
    preview.save(output/"PREVIA.jpg",quality=92)
    with zipfile.ZipFile(output/"CARROSSEL_DEBORA_PIXABAY.zip","w",zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for file in slides:
            z.write(file,arcname=file.name)
        for name in ("legenda_tiktok.txt","origem_e_licenca.json"):
            z.write(output/name,arcname=name)
    return metadata


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--job",required=True)
    p.add_argument("--output",default="outputs/debora-pixabay")
    args=p.parse_args()
    try:
        result=build_carousel(Path(args.job),Path(args.output))
        print("Carrossel finalizado usando foto real Pixabay #"+str(result["photo_id"]))
    except (CarouselError,ValueError,OSError) as exc:
        print("Falha: "+str(exc),file=sys.stderr)
        return 1
    return 0


if __name__=="__main__":
    raise SystemExit(main())
