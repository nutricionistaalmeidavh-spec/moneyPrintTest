"""Business-specific animated-slide compositions for MoneyPrint Studio V3.

All labels are illustrative, not live metrics or screenshots.
Requires only Pillow, keeps the core offline/self-hosted and paid-API free.
"""
from __future__ import annotations

from PIL import ImageDraw, ImageFont

BLUE = (101, 206, 235)
WHITE = (242, 248, 252)
MUTED = (164, 183, 201)
PANEL = (25, 46, 68)
BORDER = (56, 99, 128)
GREEN = (119, 220, 172)
GOLD = (230, 182, 111)

DIAGRAMS = {
    "erpnext": (("VENDA", "ESTOQUE", "FINANCEIRO"), ("Planilhas isoladas", "Gestão integrada")),
    "twenty": (("CONTATO", "PROPOSTA", "VENDA"), ("Leads esquecidos", "Funil acompanhado")),
    "chatwoot": (("MENSAGEM", "ATENDENTE", "RESOLUÇÃO"), ("Caixas separadas", "Atendimento central")),
    "plane": (("A FAZER", "EM ANDAMENTO", "CONCLUÍDO"), ("Tarefas dispersas", "Progresso visível")),
    "paperless": (("DOCUMENTO", "INDEXAÇÃO", "BUSCA"), ("Pastas e anexos", "Arquivos pesquisáveis")),
}


def business_diagram(scene: dict):
    context = " ".join(str(scene.get(k, "")) for k in ("title", "eyebrow", "repo_url")).casefold()
    for key, value in DIAGRAMS.items():
        if key in context:
            return value
    if "crm" in context or "funil" in context or "lead" in context:
        return DIAGRAMS["twenty"]
    if "atendimento" in context or "conversa" in context:
        return DIAGRAMS["chatwoot"]
    if "projeto" in context or "kanban" in context:
        return DIAGRAMS["plane"]
    if "documento" in context or "contrato" in context or "pdf" in context:
        return DIAGRAMS["paperless"]
    if "estoque" in context or "financeiro" in context:
        return DIAGRAMS["erpnext"]
    return (("ENTRADA", "ORGANIZAÇÃO", "RESULTADO"), ("Processos separados", "Informações organizadas"))


def _font(px: int, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/lato/Lato-Bold.ttf" if bold else "/usr/share/fonts/truetype/lato/Lato-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for item in candidates:
        try:
            return ImageFont.truetype(item, max(10, px))
        except OSError:
            continue
    return ImageFont.load_default()


def _center_text(d, rect, value, px, fill=WHITE, bold=False):
    font = _font(px, bold)
    x0, y0, x1, y1 = rect
    while d.textlength(value, font=font) > x1-x0-18 and px>10:
        px -= 2
        font = _font(px, bold)
    box = d.textbbox((0, 0), value, font=font)
    d.text(((x0+x1-(box[2]-box[0]))/2, (y0+y1-(box[3]-box[1]))/2-box[1]),
           value, font=font, fill=fill)


def _round(d, rect, fill=PANEL, outline=BORDER, radius=18, width=2):
    d.rounded_rectangle(tuple(int(v) for v in rect), radius=max(3,int(radius)),
                        fill=fill, outline=outline, width=max(1,int(width)))


def _arrow(d, x0, y, x1, thickness, color=BLUE):
    d.line((x0,y,x1,y), fill=color, width=max(2,int(thickness)))
    unit=max(6,int(thickness*3))
    d.polygon([(x1,y),(x1-unit,y-unit*.6),(x1-unit,y+unit*.6)], fill=color)


def _flow(d, labels, w, h, pad, portrait):
    if portrait:
        gap=int(h*.025)
        top=int(h*.47)
        card_h=int(h*.13)
        left=pad
        right=w-pad
        for i,label in enumerate(labels):
            y=top+i*(card_h+gap)
            _round(d,(left,y,right,y+card_h),radius=int(w*.024))
            d.ellipse((left+int(w*.05),y+int(card_h*.31),
                       left+int(w*.12),y+int(card_h*.69)),fill=(54,132,163))
            _center_text(d,(left+int(w*.16),y,right-int(w*.025),y+card_h),
                         label,int(w*.045),bold=True)
            if i<2:
                ax=w//2
                d.line((ax,y+card_h+3,ax,y+card_h+gap-6),fill=BLUE,width=max(2,int(w*.004)))
                d.polygon([(ax,y+card_h+gap-2),(ax-6,y+card_h+gap-10),
                           (ax+6,y+card_h+gap-10)],fill=BLUE)
        return
    top=int(h*.50)
    card_h=int(h*.31)
    gap=int(w*.038)
    card_w=(w-2*pad-2*gap)//3
    for i,label in enumerate(labels):
        x=pad+i*(card_w+gap)
        _round(d,(x,top,x+card_w,top+card_h),radius=int(w*.011))
        _center_text(d,(x+15,top+int(card_h*.16),x+card_w-15,top+int(card_h*.74)),
                     label,int(w*.023),bold=True)
        d.rounded_rectangle((x+int(card_w*.21),top+int(card_h*.8),
                             x+int(card_w*.79),top+int(card_h*.825)),
                            radius=3, fill=(72,152,181))
        if i<2:
            _arrow(d,x+card_w+4,top+card_h//2,x+card_w+gap-7,max(2,int(w*.002)))


def _comparison(d, before_after, w, h, pad, portrait):
    pairs = [("ANTES",before_after[0],(65,78,98)),("COM OPEN SOURCE",before_after[1],(32,89,95))]
    top=int(h*.48) if not portrait else int(h*.46)
    if portrait:
        card_w=w-2*pad
        card_h=int(h*.17)
        gap=int(h*.033)
    else:
        card_w=(w-2*pad-int(w*.025))//2
        card_h=int(h*.27)
        gap=int(w*.025)
    for i,(label,description,color) in enumerate(pairs):
        x=pad if portrait else pad+i*(card_w+gap)
        y=top+i*(card_h+gap) if portrait else top
        _round(d,(x,y,x+card_w,y+card_h),fill=color,radius=int(min(w,h)*.017))
        lf=_font(max(13,int(w*(.019 if not portrait else .04))),True)
        d.text((x+int(card_w*.065),y+int(card_h*.17)),label,font=lf,
               fill=GOLD if i==0 else GREEN)
        _center_text(d,(x+int(card_w*.035),y+int(card_h*.38),
                        x+card_w-int(card_w*.035),y+card_h-int(card_h*.08)),
                     description,int(w*(.03 if not portrait else .048)),bold=True)


def _repo_badges(d, w,h,pad, portrait):
    tags=["Código público","Self-hosted","Sem API paga"]
    base_y=int(h*.62) if not portrait else int(h*.57)
    for i,tag in enumerate(tags):
        x=pad if not portrait else pad
        y=base_y+i*int(h*.07)
        cw=int(w*.37) if not portrait else w-2*pad
        _round(d,(x,y,x+cw,y+int(h*.054)),fill=(29,54,78),radius=int(min(w,h)*.009))
        font=_font(max(13,int(w*(.019 if not portrait else .041))),True)
        d.text((x+int(w*.016),y+int(h*.011)),tag,font=font,fill=(195,228,239))


def _outro(d,w,h,pad,portrait):
    labels=["ERPNext","Twenty CRM","Chatwoot","Plane","Paperless-ngx"]
    cols=1 if portrait else 3
    start=int(h*.48) if not portrait else int(h*.48)
    cw=(w-2*pad-int(w*.02)*(cols-1))//cols
    ch=int(h*(.16 if not portrait else .069))
    gap=int(w*.02) if not portrait else int(h*.014)
    for i,label in enumerate(labels):
        col=i%cols
        row=i//cols
        x=pad+col*(cw+gap)
        y=start+row*(ch+gap)
        _round(d,(x,y,x+cw,y+ch),fill=(28,57,78),radius=max(8,int(w*.009)))
        _center_text(d,(x+7,y,x+cw-7,y+ch),label,
                     max(14,int(w*(.021 if not portrait else .046))),bold=True)


def paint_layout(image, scene: dict, pad: int, title_bottom: int,
                 width: int, height: int, has_asset: bool) -> None:
    """Paint relevant diagram, comparison or project selector below the title."""
    d=ImageDraw.Draw(image)
    layout=scene.get("layout","hero")
    portrait=height>width
    labels, before_after=business_diagram(scene)
    if layout=="flow":
        _flow(d,labels,width,height,pad,portrait)
    elif layout=="split":
        _comparison(d,before_after,width,height,pad,portrait)
    elif layout=="browser":
        _repo_badges(d,width,height,pad,portrait)
    elif layout in ("minimal","quote"):
        _outro(d,width,height,pad,portrait)
    elif layout=="hero":
        labels=("GESTÃO","ATENDIMENTO","PRODUTIVIDADE")
        _flow(d,labels,width,height,pad,portrait)
