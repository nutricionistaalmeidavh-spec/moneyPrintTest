"""Curadoria editorial - fotografias de extração e armazenamento de leite materno.
Uso: python scripts/curate_photos_pdf.py
Não utiliza API paga. Fontes: Pixabay público e Wikimedia Commons.
"""
from __future__ import annotations

import html
import io
import json
import re
import time
from pathlib import Path

import requests
from PIL import Image, ImageOps, ImageDraw, ImageFont
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "curadoria_amamentacao"
IMAGES = OUT / "fotos"
PDF = OUT / "10_fotos_semelhantes_amamentacao.pdf"
API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {
    "User-Agent": "MoneyPrintTestCuradoria/1.0 (https://github.com/nutricionistaalmeidavh-spec/moneyPrintTest; search attribution)",
    "Accept": "application/json, image/*",
}
SEEDS = [
    {"bank":"Pixabay", "title":"Bolsas de leite materno ordenhado", "author":"JillWellington",
     "url":"https://pixabay.com/photos/breast-milk-mothers-milk-9607237/",
     "img":"https://cdn.pixabay.com/photo/2025/05/18/13/32/breast-milk-9607237_640.jpg",
     "license":"Pixabay Content License", "license_url":"https://pixabay.com/service/license-summary/",
     "note":"Sacos transparentes de armazenamento; leite visível no primeiro plano"},
    {"bank":"Pixabay", "title":"Detalhe de bico de mamadeira", "author":"tatlin",
     "url":"https://pixabay.com/photos/baby-bottles-milk-bottle-child-100111/",
     "img":"https://cdn.pixabay.com/photo/2013/04/03/18/39/baby-bottles-100111_1280.jpg",
     "license":"Pixabay Content License", "license_url":"https://pixabay.com/service/license-summary/",
     "note":"Close de objeto de alimentação; enquadramento com espaço para texto"},
    {"bank":"Pixabay", "title":"Mamadeira em uso", "author":"ManuelPacheco",
     "url":"https://pixabay.com/photos/feeding-bottle-milk-newborn-child-784486/",
     "img":"https://cdn.pixabay.com/photo/2015/05/26/10/38/biberon-784486_1280.jpg",
     "license":"Pixabay Content License", "license_url":"https://pixabay.com/service/license-summary/",
     "note":"Mamadeira em primeiro plano durante alimentação"},
]
COMMONS = [
    ("Bottle of Pumped Breast Milk.jpg","Frasco de leite com parte da bomba","Coletor e flange visíveis em fotografia caseira"),
    ("Bottles of Pumped Breast Milk.jpg","Frascos de leite materno extraído","Volumes de leite e componentes da bomba em close"),
    ("Full Bottles of Pumped Breast Milk.jpg","Frascos cheios com leite ordenhado","Enquadramento direto em dois recipientes"),
    ("Breast milk storage containers bottles.JPG","Frascos e recipientes de armazenamento","Fotografia real com diversas mamadeiras"),
    ("Medela lactaline select breast pump.jpg","Bomba tira-leite e recipientes","Equipamento e garrafas sobre fundo cotidiano"),
    ("Manual Breast Pump 2005 SeanMcClean.jpg","Bomba manual com frasco","Enquadramento vertical de acessório de extração"),
    ("Avent breast pump for double sides by Hsuanling.jpg","Bomba extratora dupla","Bomba e acessórios com tubos de coleta"),
    ("Breast Pump (50265746936).jpg","Bomba extratora em contexto real","Registro de equipamento de amamentação"),
    ("Breast Pump - Nursery (50265747136).jpg","Bomba em ambiente de cuidados","Fotografia de bomba extratora em ambiente"),
    ("Breast pumping.jpg","Extração de leite em contexto cotidiano","Fotografia documental de ordenha"),
    ("Ameda lactaline personal breast pump.JPG","Bomba elétrica de extração","Produto e frascos em cena natural"),
    ("Handmilchpumpe-2.jpg","Bomba manual de leite","Equipamento de extração fotografado de perto"),
    ("Avent isis breast pump.jpg","Bomba manual e mamadeira","Bomba em conjunto com frasco"),
    ("Breast Pump Parts 1.JPG","Peças de bomba extratora","Acessórios e recipientes da bomba"),
    ("Breast Pump Parts 2.JPG","Componentes da bomba extratora","Enquadramento de peças e conexões"),
]
S = requests.Session()
S.headers.update(HEADERS)

def get_bytes(url:str, referer:str="") -> bytes:
    if not url.startswith("https://"):
        raise ValueError("Somente HTTPS")
    last_error = None
    for trial in range(3):
        try:
            headers = {"Referer": referer} if referer else {}
            with S.get(url, headers=headers, timeout=(12, 55), stream=True) as r:
                r.raise_for_status()
                if not r.headers.get("content-type","").startswith("image/"):
                    raise ValueError("Retorno não é imagem")
                blocks = []
                total=0
                for block in r.iter_content(1024*256):
                    total+=len(block)
                    if total>12*1024*1024:
                        raise ValueError("Imagem acima de 12 MB")
                    blocks.append(block)
                return b"".join(blocks)
        except (requests.RequestException, ValueError) as exc:
            last_error=exc
            time.sleep(1+trial)
    raise RuntimeError(str(last_error))

def commons_entry(name, title, note):
    params={
        "action":"query", "format":"json","formatversion":"2","prop":"imageinfo",
        "titles":"File:"+name, "iiprop":"url|size|mime|extmetadata",
        "iiurlwidth":"1280",
    }
    result=S.get(API,params=params,timeout=40).json()
    pages=result.get("query",{}).get("pages",[])
    if not pages or "imageinfo" not in pages[0]:
        raise ValueError("Sem metadados")
    info=pages[0]["imageinfo"][0]
    props=info.get("extmetadata") or {}
    def clean(key):
        val=(props.get(key) or {}).get("value","")
        return re.sub(r"<[^>]+>", " ", html.unescape(val)).strip()
    lic=clean("LicenseShortName") or clean("UsageTerms")
    if not lic or "nc" in lic.lower().split() or "nd" in lic.lower().split():
        raise ValueError("Licença não identificada ou com restrições incompatíveis")
    permissible=any(token in lic.lower() for token in ["cc by","cc0","public domain","pd-","domínio público"])
    if not permissible:
        raise ValueError("Licença fora da lista aprovada: "+lic)
    author=clean("Artist") or clean("Credit") or "Autoria informada na página"
    if len(author)>110: author=author[:107]+"..."
    lic_url=(props.get("LicenseUrl") or {}).get("value","")
    source="https://commons.wikimedia.org/wiki/File:"+name.replace(" ","_")
    if not lic_url: lic_url=source
    return {"bank":"Wikimedia Commons","title":title,"author":author,"url":source,
            "img":info.get("thumburl") or info["url"], "license":lic,"license_url":lic_url,
            "note":note}

def save_image(blob:bytes, index:int) -> str:
    image=Image.open(io.BytesIO(blob))
    image=ImageOps.exif_transpose(image)
    if image.mode not in ("RGB","L"):
        if image.mode=="RGBA":
            bg=Image.new("RGB",image.size,"white")
            bg.paste(image,mask=image.getchannel("A"))
            image=bg
        else: image=image.convert("RGB")
    elif image.mode=="L": image=image.convert("RGB")
    if min(image.size)<270:
        raise ValueError("Resolução muito baixa")
    image.thumbnail((1550,1800),Image.Resampling.LANCZOS)
    path=IMAGES/f"foto_{index:02d}.jpg"
    image.save(path,quality=86, optimize=True)
    return str(path)

def collect():
    IMAGES.mkdir(parents=True,exist_ok=True)
    selected=[]
    attempts=[]
    for seed in SEEDS:
        try:
            path=save_image(get_bytes(seed["img"],seed["url"]),len(selected)+1)
            selected.append({**seed,"file":path})
            print(f"OK [{len(selected)}] {seed['bank']} {seed['title']}",flush=True)
        except Exception as e:
            attempts.append({"source":seed["url"],"error":str(e)})
            print("REJEITADO PIXABAY: "+str(e),flush=True)
    for name,title,note in COMMONS:
        if len(selected)>=10: break
        try:
            entry=commons_entry(name,title,note)
            blob=get_bytes(entry["img"],entry["url"])
            path=save_image(blob,len(selected)+1)
            selected.append({**entry,"file":path})
            print(f"OK [{len(selected)}] Commons {name} [{entry['license']}]",flush=True)
        except Exception as e:
            attempts.append({"source":name,"error":str(e)})
            print(f"REJEITADO Commons {name}: {e}",flush=True)
    (OUT/"metadados.json").write_text(json.dumps({"selected":selected,"attempts":attempts},
        indent=2,ensure_ascii=False),encoding="utf-8")
    if len(selected)!=10:
        raise RuntimeError(f"Apenas {len(selected)} imagens elegíveis; não inventar fotos")
    if not any(x["bank"]=="Pixabay" for x in selected):
        raise RuntimeError("Pixabay não retornou fotos verificáveis; não afirmar que foi usado")
    return selected

W,H=595.276,841.89
INK=HexColor("#0E2438"); SEA=HexColor("#007D82"); GRAY=HexColor("#5C6975")
def font():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    pdfmetrics.registerFont(TTFont("DejaVu","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("DejaVuBold","/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))

def textwrap(txt, maxlen=92):
    words=txt.split(); lines=[]; buf=""
    for word in words:
        if len((buf+" "+word).strip())>maxlen and buf:
            lines.append(buf);buf=word
        else:buf=(buf+" "+word).strip()
    if buf:lines.append(buf)
    return lines

def draw_fit(c,path,x,y,width,height):
    im=Image.open(path); iw,ih=im.size
    ratio=min(width/iw,height/ih)
    ww,hh=iw*ratio,ih*ratio
    c.drawImage(ImageReader(im),x+(width-ww)/2,y+(height-hh)/2,ww,hh,mask='auto')
    return ww,hh

def make_pdf(selected):
    c=Canvas(str(PDF),pagesize=(W,H))
    c.setTitle("10 fotos para carrosséis de amamentação | curadoria MoneyPrint")
    c.setFillColor(INK);c.setFont("DejaVuBold",22)
    c.drawString(35,H-52,"10 fotografias para carrosséis")
    c.setFont("DejaVu",11);c.setFillColor(GRAY)
    c.drawString(35,H-76,"Amamentação / extração / armazenamento | Pesquisa gratuita")
    c.setFillColor(SEA);c.rect(35,H-87,525,3,fill=1,stroke=0)
    # Contact sheet: duas colunas x cinco linhas
    for i,obj in enumerate(selected):
        col=i%2; row=i//2
        x=35+col*266; y=H-120-row*129
        c.setFillColor(HexColor("#F1F6F5"))
        c.roundRect(x,y-99,252,100,8,fill=1,stroke=0)
        draw_fit(c,obj["file"],x+5,y-94,242,90)
        c.setFillColor(INK); c.setFont("DejaVuBold",9.2)
        c.drawString(x,y-113,f"{i+1:02d}  {obj['bank']}") 
    c.setFillColor(GRAY);c.setFont("DejaVu",8)
    c.drawString(35,35,"Fotos com licenças registradas; verificar condições antes da publicação.")
    c.showPage()
    for i,obj in enumerate(selected):
        c.setFillColor(INK);c.setFont("DejaVuBold",16)
        c.drawString(35,H-52,f"{i+1:02d}  {obj['title'][:46]}")
        c.setFillColor(SEA); c.setFont("DejaVuBold",10)
        c.drawString(35,H-73,obj["bank"])
        c.setFillColor(HexColor("#F1F6F5"))
        c.roundRect(34,143,527,593,10,fill=1,stroke=0)
        draw_fit(c,obj["file"],42,155,511,569)
        c.setFillColor(INK);c.setFont("DejaVu",10)
        yy=125
        for line in textwrap(obj["note"],85)[:2]:
            c.drawString(35,yy,line);yy-=15
        c.setFillColor(GRAY);c.setFont("DejaVu",8.2)
        who=obj["author"]
        if len(who)>96:who=who[:93]+"..."
        c.drawString(35,82,"Autor/crédito: "+who)
        c.drawString(35,66,"Licença: "+obj["license"][:84])
        c.setFillColor(SEA);c.setFont("DejaVu",8.5)
        c.drawString(35,47,"Abrir fotografia original e termos de uso (link)")
        c.linkURL(obj["url"], (32,43,545,59),relative=0,thickness=0)
        c.setFillColor(GRAY);c.drawString(35,31,"Créditos e condições detalhadas em metadados.json")
        c.showPage()
    c.setFillColor(INK);c.setFont("DejaVuBold",20)
    c.drawString(35,H-52,"Licenças, fontes e recomendações")
    c.setFont("DejaVu",10);c.setFillColor(GRAY)
    y=H-89
    for paragraph in [
        "A seleção prioriza fotografia real, frascos, equipamentos e luz natural.",
        "Pixabay: licença de conteúdo, com restrições para marcas, pessoas e redistribuição.",
        "Wikimedia: observar atribuição e eventual compartilhamento pela mesma licença (SA).",
        "A referência original do usuário não foi incluída entre as imagens selecionadas.",
        "Link de cada fotografia na respectiva página. Material para análise, não post final.",
    ]:
        for line in textwrap(paragraph,87):
            c.drawString(35,y,line);y-=16
        y-=8
    y-=12
    for i,obj in enumerate(selected):
        c.setFont("DejaVuBold",9);c.setFillColor(INK)
        c.drawString(35,y,f"{i+1:02d}  {obj['title'][:75]}")
        y-=15
        c.setFont("DejaVu",7.7);c.setFillColor(SEA)
        url=obj["url"]
        display=(url[:99]+"...") if len(url)>99 else url
        c.drawString(35,y,display);c.linkURL(url,(32,y-2,550,y+11),relative=0,thickness=0)
        y-=29
    c.save()

def main():
    font()
    selected=collect()
    make_pdf(selected)
    print("PDF GERADO:",PDF,"bytes",PDF.stat().st_size,flush=True)

if __name__=="__main__":
    main()
