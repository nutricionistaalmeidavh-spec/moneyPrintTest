"""Carrosséis fotográficos gratuitos (Pixabay/Commons + Pillow + Ollama local).

Sem imagens de IA, publicação automática, APIs pagas ou entrega da foto original.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from urllib.request import Request, urlopen
import zipfile

from scripts.carousel_media import (
    PhotoError, choose_candidate, download_photo, parse_candidates,
    parse_pixabay_candidates, safe_photo_url, search_free_photos,
)

WIDTH, HEIGHT = 1080, 1920
COMMIT_PATTERN = re.compile(r"[a-f0-9]{40}\Z")
REQUEST_PATTERN = re.compile(r"carousel_requests/[A-Za-z0-9][A-Za-z0-9_.-]{0,100}\.json\Z")
DEFAULT_TERMS = ["desk setup computer monitor laptop window",
                 "modern home office monitor plants",
                 "dual monitor workstation desk",
                 "bright minimalist desk setup"]
VALID_STYLES = {"reference", "brush", "cinematic", "minimal", "contrast"}
IMAGE_HEIGHT = {"4:5": 1350, "9:16": 1920}


class CarouselError(ValueError):
    pass


def _one_line(value, field, limit, *, allow_empty=False):
    if not isinstance(value, str) or len(value.strip()) > limit or (
        not allow_empty and not value.strip()
    ) or any(c in value for c in "\r\n\x00"):
        raise CarouselError(field + " inválido")
    return value.strip()


def validate_request(raw):
    if not isinstance(raw, dict):
        raise CarouselError("Pedido deve ser objeto JSON")
    allowed = {"topic", "slides", "slide_count", "photo_mode", "photo_terms",
               "source", "style", "items", "cta", "brand", "hashtags", "only_pages", "aspect", "photo_id"}
    if set(raw) - allowed:
        raise CarouselError("Campos não permitidos: " + ", ".join(sorted(set(raw) - allowed)))
    topic = _one_line(raw.get("topic"), "topic", 280)
    count = raw.get("slide_count", 6)
    if type(count) is not int or not 2 <= count <= 10:
        raise CarouselError("slide_count deve estar entre 2 e 10")
    only_pages = raw.get("only_pages", list(range(1, count + 1)))
    if (not isinstance(only_pages, list) or not 1 <= len(only_pages) <= count or
        any(type(page) is not int or not 1 <= page <= count for page in only_pages) or
        len(set(only_pages)) != len(only_pages)):
        raise CarouselError("only_pages deve conter páginas únicas entre 1 e slide_count")
    only_pages = sorted(only_pages)
    mode = raw.get("photo_mode", "same")
    if mode not in ("same", "varied"):
        raise CarouselError("photo_mode inválido")
    source = raw.get("source", "auto")
    if source not in ("auto", "wikimedia", "pixabay"):
        raise CarouselError("source inválido: somente fontes gratuitas permitidas")
    photo_id = raw.get("photo_id")
    if photo_id is not None and (
        type(photo_id) is not int or not 1 <= photo_id <= 999999999 or
        source == "wikimedia"
    ):
        raise CarouselError("photo_id requer ID inteiro de foto Pixabay e fonte auto/pixabay")
    style = raw.get("style", "reference")
    if style not in VALID_STYLES:
        raise CarouselError("style inválido")
    aspect = raw.get("aspect", "4:5" if style in ("reference", "brush") else "9:16")
    if aspect not in IMAGE_HEIGHT or (style not in ("reference", "brush") and aspect != "9:16"):
        raise CarouselError("aspect não compatível com o estilo")
    brand = _one_line(raw.get("brand", "ArtiSys"), "brand", 32)
    cta = _one_line(raw.get("cta", "Salve este post para consultar depois."),
                    "cta", 140)
    terms = raw.get("photo_terms", DEFAULT_TERMS)
    if not isinstance(terms, list) or not 1 <= len(terms) <= 8:
        raise CarouselError("photo_terms deve conter de 1 a 8 termos")
    terms = [_one_line(t, "termo de foto", 90) for t in terms]
    slides = raw.get("slides", [])
    if not isinstance(slides, list) or (slides and len(slides) != count):
        raise CarouselError("slides deve conter exatamente slide_count páginas")
    normalized_slides = []
    for slide in slides:
        if not isinstance(slide, dict) or set(slide) - {"title", "body", "highlight"}:
            raise CarouselError("Página inválida")
        normalized = {
            "title": _one_line(slide.get("title"), "title", 96),
            "body": _one_line(slide.get("body", ""), "body", 260,
                              allow_empty=True),
        }
        if "highlight" in slide:
            normalized["highlight"] = _one_line(
                slide.get("highlight"), "highlight", 84, allow_empty=True)
        normalized_slides.append(normalized)
    items = raw.get("items", [])
    if not isinstance(items, list) or len(items) > 8:
        raise CarouselError("items deve ser uma lista de até 8 itens")
    normalized_items = []
    for item in items:
        if not isinstance(item, dict) or set(item) - {"name", "url", "detail"}:
            raise CarouselError("item inválido")
        name = _one_line(item.get("name"), "item.name", 80)
        detail = _one_line(item.get("detail", ""), "item.detail", 180,
                           allow_empty=True)
        url = _one_line(item.get("url", ""), "item.url", 300, allow_empty=True)
        if url:
            from urllib.parse import urlsplit
            parsed = urlsplit(url)
            if (parsed.scheme != "https" or not parsed.hostname or
                parsed.username or parsed.password):
                raise CarouselError("item.url precisa ser HTTPS público")
        normalized_items.append({"name": name, "url": url, "detail": detail})
    hashtags = raw.get("hashtags", ["#tecnologia", "#programacao", "#ArtiSys"])
    if not isinstance(hashtags, list) or len(hashtags) > 10 or any(
        not isinstance(tag, str) or not re.fullmatch(r"#[\wÀ-ÿ]{2,35}", tag)
        for tag in hashtags
    ):
        raise CarouselError("hashtags inválidas")
    return {
        "topic": topic, "slide_count": count, "photo_mode": mode,
        "photo_terms": terms, "source": source, "photo_id": photo_id,
        "style": style, "aspect": aspect,
        "slides": normalized_slides,
        "items": normalized_items, "brand": brand, "cta": cta, "hashtags": hashtags,
        "only_pages": only_pages,
    }


def select_requests(root, *, manual="", before="", after=""):
    root = Path(root).resolve()
    if manual:
        names = [manual]
    else:
        if not COMMIT_PATTERN.fullmatch(before) or not COMMIT_PATTERN.fullmatch(after):
            raise CarouselError("Commits de push inválidos")
        changed = subprocess.run([
            "git", "diff", "--diff-filter=A", "--name-only", before, after, "--",
            "carousel_requests/"
        ], cwd=root, check=True, capture_output=True, text=True)
        names = changed.stdout.splitlines()
    names = sorted(set(names))
    if not 1 <= len(names) <= 4:
        raise CarouselError("Crie de 1 a 4 novos pedidos por execução")
    paths = []
    for name in names:
        if not REQUEST_PATTERN.fullmatch(name) or name.startswith("carousel_requests/."):
            raise CarouselError("Caminho inseguro de pedido")
        path = (root / name).resolve()
        if not path.is_relative_to(root / "carousel_requests") or not path.is_file():
            raise CarouselError("Pedido inexistente ou fora de carousel_requests")
        paths.append(path)
    return paths


def _get_font(size, bold=True):
    from PIL import ImageFont
    path = ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    if Path(path).is_file():
        return ImageFont.truetype(path, size)
    for backup in ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(backup, size)
        except OSError:
            pass
    raise CarouselError("Fonte TrueType não disponível; instale fonts-dejavu-core")


def _wrap(draw, text, font, max_width):
    """Wrap by rendered pixel width; break overly long tokens safely."""
    lines = []
    for paragraph in text.split("\n"):
        current = ""
        for word in paragraph.split():
            candidate = (current + " " + word).strip()
            if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
                current = ""
            for char in word:
                attempted = current + char
                if current and draw.textbbox((0, 0), attempted, font=font)[2] > max_width:
                    lines.append(current)
                    current = char
                else:
                    current = attempted
        if current:
            lines.append(current)
    return lines


def _fit_lines(draw, text, max_width, max_lines, initial, minimum, bold=True):
    for size in range(initial, minimum - 1, -2):
        font = _get_font(size, bold)
        lines = _wrap(draw, text, font, max_width)
        if len(lines) <= max_lines:
            return font, lines, size
    raise CarouselError("Texto não cabe na imagem; reduza o conteúdo")


def _cover(photo, aspect="4:5"):
    from PIL import Image, ImageOps
    with Image.open(photo) as input_image:
        original = ImageOps.exif_transpose(input_image)
        rgb = original.convert("RGB")
    return ImageOps.fit(rgb, (WIDTH, IMAGE_HEIGHT[aspect]), method=Image.Resampling.LANCZOS,
                        centering=(0.5, 0.5))


def _make_reference_page(background, slide, req, index, total):
    """Original TikTok photo-post aesthetic: photo first, centered outlined type.

    No branding badge, artificial gradient, footer, progress strip or screenshots
    of social-network UI. Keep the photograph prominent, not a backdrop to UI.
    """
    from PIL import ImageDraw
    image = background.copy().convert("RGB")
    draw = ImageDraw.Draw(image)
    w, h = image.size
    max_width = int(w * 0.88)
    title_font, title_lines, title_size = _fit_lines(
        draw, slide["title"], max_width, 4, 65 if index == 1 else 80,
        52 if index == 1 else 58)
    body_font, body_lines, body_size = (
        _fit_lines(draw, slide["body"], max_width, 3,
                   59 if index == 1 else 55, 38)
        if slide["body"] else (_get_font(44), [], 44))
    title_step = int(title_size * 1.15)
    body_step = int(body_size * 1.22)
    title_height = title_step * len(title_lines)
    body_height = body_step * len(body_lines)
    gap = int(h * .052) if body_lines else 0
    # The reference places the main statement around 41-50% of the photo,
    # secondary sentence around 57%, and swipe chevrons below.
    group_height = title_height + gap + body_height
    first_line_y = max(int(h * .26), int(h * .48 - group_height * .48))
    if first_line_y + group_height > int(h * .78):
        first_line_y = int(h * .78) - group_height
    if first_line_y < int(h * .19):
        raise CarouselError("Texto muito longo para o formato da foto")
    def paint(lines, font, y, line_height, stroke):
        for line in lines:
            draw.text((w // 2, y), line, anchor="mt", font=font,
                      fill=(255, 255, 255), stroke_width=stroke,
                      stroke_fill=(0, 0, 0))
            y += line_height
        return y
    y = paint(title_lines, title_font, first_line_y, title_step, 7)
    if body_lines:
        y = paint(body_lines, body_font, y + gap, body_step, 6)
    if index == 1:
        arrow_y = max(int(h * .66), y + int(h * .035))
        if arrow_y < int(h * .86):
            arrows = "›" * 14
            arrow_font = _get_font(55)
            draw.text((w // 2, arrow_y), arrows.strip(), anchor="mt",
                      font=arrow_font, fill="white", stroke_width=4,
                      stroke_fill="black")
    return image


def _make_brush_page(background, slide, req, index, total):
    """Full photo, large central text, white brush stroke with crisp black lettering.

    The source photograph remains visible; no dashboards, rectangles, logos or
    hard black outlines. Works entirely with Pillow; no image AI or paid service.
    """
    from PIL import Image, ImageDraw
    canvas = background.copy().convert("RGB")
    draw = ImageDraw.Draw(canvas)
    w, h = canvas.size
    max_width = int(w * .89)
    intro = slide["title"]
    highlighted = slide.get("highlight", "")
    # Other pages get a brush headline automatically.
    if not highlighted:
        highlighted, intro = intro, ""
    intro_font, intro_lines, intro_sz = (
        _fit_lines(draw, intro, max_width, 3, 65, 38)
        if intro else (_get_font(42), [], 42))
    brush_font, brush_lines, brush_sz = _fit_lines(
        draw, highlighted, max_width - 80, 3, 76, 42)
    body = slide.get("body", "")
    body_font, body_lines, body_sz = (
        _fit_lines(draw, body, max_width, 4, 49, 30, bold=False)
        if body else (_get_font(36, False), [], 36))
    intro_step = round(intro_sz * 1.18)
    brush_step = round(brush_sz * 1.20)
    body_step = round(body_sz * 1.25)
    intro_h = len(intro_lines) * intro_step
    brush_h = len(brush_lines) * brush_step
    body_h = len(body_lines) * body_step
    gap1, gap2 = 24, 38
    block_height = intro_h + (gap1 if intro_lines else 0) + brush_h + (
        gap2 + body_h if body_lines else 0)
    y = max(round(h * .25), round(h * .47 - block_height * .45))
    if y + block_height > round(h * .82):
        y = round(h * .82) - block_height
    if y < round(h * .13):
        raise CarouselError("Texto excede área segura; diminua o conteúdo")
    def centered_text(text, font, top, color, shadow=True):
        # Soft offset shadow, never the heavy stroked font from the old renderer.
        if shadow:
            draw.text((w // 2 + 3, top + 3), text, anchor="mt",
                      font=font, fill=(0, 0, 0))
        draw.text((w // 2, top), text, anchor="mt", font=font, fill=color)
    for line in intro_lines:
        centered_text(line, intro_font, y, "white")
        y += intro_step
    if intro_lines:
        y += gap1
    for i, line in enumerate(brush_lines):
        box = draw.textbbox((0, 0), line, font=brush_font)
        text_w = box[2] - box[0]
        half_w = min(int(w * .47), round(text_w / 2 + 34))
        left, right = w // 2 - half_w, w // 2 + half_w
        band_y1 = y - 8
        band_y2 = y + brush_step - 4
        wave = 8
        polygon = [(left + 18, band_y1)]
        for x in range(left + 18, right - 10, 31):
            polygon.append((x, band_y1 + ((x + i * 13) % 7) - 3))
        polygon += [(right - 14, band_y1 + 6),
                    (right + 8, band_y1 + 14),
                    (right - 2, band_y2 - 5)]
        for x in range(right - 8, left + 8, -29):
            polygon.append((x, band_y2 + ((x + 3 * i) % 7) - 2))
        polygon += [(left - 11, band_y2 - 12), (left - 6, band_y1 + 11)]
        draw.polygon(polygon, fill="white")
        # The label sits wholly inside the highlight so no pixelated stroke.
        centered_text(line, brush_font, y, "black", shadow=False)
        y += brush_step
    if body_lines:
        y += gap2
        for line in body_lines:
            centered_text(line, body_font, y, "white")
            y += body_step
    if index == 1:
        arrow_y = max(round(h * .75), y + 38)
        if arrow_y <= round(h * .88):
            font = _get_font(51)
            centered_text("››››››››››", font, arrow_y, "white")
    return canvas


def _make_page(background, slide, req, index, total):
    if req["style"] == "reference":
        return _make_reference_page(background, slide, req, index, total)
    if req["style"] == "brush":
        return _make_brush_page(background, slide, req, index, total)
    from PIL import Image, ImageDraw
    photo = background.copy().convert("RGBA")
    shade = Image.new("RGBA", (WIDTH, HEIGHT))
    pixels = ImageDraw.Draw(shade)
    if req["style"] == "minimal":
        alpha_start, alpha_end = 20, 205
    elif req["style"] == "contrast":
        alpha_start, alpha_end = 55, 245
    else:
        alpha_start, alpha_end = 30, 232
    for y in range(HEIGHT):
        fraction = y / HEIGHT
        strength = max(0, (fraction - 0.20) / 0.80)
        alpha = int(alpha_start + (alpha_end - alpha_start) * strength ** 1.5)
        pixels.line((0, y, WIDTH, y), fill=(4, 12, 25, alpha))
    photo = Image.alpha_composite(photo, shade)
    draw = ImageDraw.Draw(photo)
    margin, right = 78, WIDTH - 78
    draw.rounded_rectangle((margin, 124, 450, 192), radius=28,
                           fill=(0, 0, 0, 132))
    draw.text((margin + 20, 143), req["brand"].upper() + "  /  TECH",
              font=_get_font(25), fill="white", stroke_width=0)
    draw.text((WIDTH - 175, 142), f"{index:02d}/{total:02d}",
              font=_get_font(27), fill=(230, 240, 251))
    draw.rounded_rectangle((margin, 1715, right, 1726), radius=5, fill=(160, 174, 190, 120))
    step = int((right - margin) * index / total)
    draw.rounded_rectangle((margin, 1715, margin + step, 1726), radius=5,
                           fill=(241, 248, 253, 255))
    title_font, title_lines, title_size = _fit_lines(
        draw, slide["title"], right - margin, 5, 88, 46)
    body_font, body_lines, body_size = _fit_lines(
        draw, slide["body"], right - margin, 5, 42, 26, bold=False
    ) if slide["body"] else (_get_font(32, False), [], 32)
    title_step = int(title_size * 1.23)
    body_step = int(body_size * 1.38)
    title_height = len(title_lines) * title_step
    body_height = len(body_lines) * body_step
    gap = 34 if body_lines else 0
    total_height = title_height + gap + body_height
    base_y = 1590 - total_height
    if base_y < 710:
        raise CarouselError("Conteúdo não cabe na área segura")
    for line in title_lines:
        draw.text((margin, base_y), line, font=title_font, fill=(255, 255, 255),
                  stroke_width=3, stroke_fill=(0, 0, 0, 220))
        base_y += title_step
    if body_lines:
        base_y += gap
        for line in body_lines:
            draw.text((margin, base_y), line, font=body_font, fill=(240, 246, 252),
                      stroke_width=2, stroke_fill=(0, 0, 0, 210))
            base_y += body_step
    draw.text((margin, 1764), "DESLIZE PARA CONTINUAR" if index < total else req["cta"][:60],
              font=_get_font(24), fill=(240, 249, 252))
    return photo.convert("RGB")


def build_caption(req):
    lines = [req["topic"], ""]
    if not req["items"] and req["slides"]:
        lines.append("Neste carrossel:")
        lines.extend("• " + slide["title"] for slide in req["slides"][1:-1])
    for item in req["items"]:
        line = "• " + item["name"]
        if item["detail"]:
            line += " — " + item["detail"]
        if item["url"]:
            line += "\n" + item["url"]
        lines.append(line)
    lines.extend(["", req["cta"], "", " ".join(req["hashtags"])])
    return "\n".join(lines).strip() + "\n"


def _credit_text(records):
    result = [
        "Créditos e licenciamento das fotografias utilizadas (editadas com texto):",
        "Não redistribua as fotografias originais isoladamente.",
        "Confira também marcas, pessoas reconhecíveis e outros direitos de terceiros.",
        "",
    ]
    for item in records:
        result.append(
            f"• {item['provider']} — {item['title']} | autor: {item['author']}"
            f" | origem: {item['source']} | licença: {item['license']}"
            f" ({item['license_url']}) | alterações: recorte, gradiente e texto."
        )
    return "\n".join(result) + "\n"


def compose_carousel(req, photo, out, item):
    """Render with a single photo (all slides); never export the original photo."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    source = _cover(photo, req["aspect"])
    paths = []
    for number, slide in enumerate(req["slides"], start=1):
        if number not in req["only_pages"]:
            continue
        target = out / f"{number:02d}.jpg"
        _make_page(source, slide, req, number, len(req["slides"])).save(
            target, format="JPEG", quality=91, optimize=True, subsampling=0)
        paths.append(target)
    _deliver(req, out, paths, [item])
    return paths


def _deliver(req, out, paths, records):
    from PIL import Image, ImageOps, ImageDraw
    out = Path(out)
    (out / "legenda.txt").write_text(build_caption(req), encoding="utf-8")
    (out / "creditos.txt").write_text(_credit_text(records), encoding="utf-8")
    (out / "licencas_midia.json").write_text(
        json.dumps([{k: r[k] for k in ("provider", "title", "source", "author",
                          "license", "license_url")} for r in records],
                   ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "roteiro.json").write_text(
        json.dumps({"topic": req["topic"], "slides": req["slides"], "review_required": True,
                    "automatic_publication": False}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    # Create an overview suitable for visual approval.
    thumbs = []
    with Image.open(paths[0]) as first:
        thumb_height = round(270 * first.height / first.width)
    for path in paths:
        with Image.open(path) as img:
            thumbs.append(ImageOps.fit(img.convert("RGB"), (270, thumb_height)))
    cols = min(3, len(thumbs))
    rows = (len(thumbs) + cols - 1) // cols
    preview = Image.new("RGB", (cols * 270, rows * thumb_height), (14, 23, 33))
    for i, thumb in enumerate(thumbs):
        preview.paste(thumb, ((i % cols) * 270, (i // cols) * thumb_height))
    preview.save(out / "preview.jpg", quality=84)
    zip_path = out / "carrossel.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in paths:
            zf.write(path, path.name)
        for name in ("legenda.txt", "creditos.txt", "licencas_midia.json",
                     "roteiro.json", "preview.jpg"):
            zf.write(out / name, name)


def _generate_slides_with_local_llm(req):
    """Use the same Docker Ollama runner the video pipeline already uses."""
    from scripts.render_request import OLLAMA_MODEL, start_ollama, ollama_ready
    started = False
    try:
        started = start_ollama()
        facts = [{"name": i["name"], "detail": i["detail"], "url": i["url"]}
                 for i in req["items"]]
        prompt = (
            "Você cria carrosséis de redes sociais com texto curto e natural em português "
            "brasileiro. Retorne EXCLUSIVAMENTE JSON com a chave slides contendo exatamente "
            f"{req['slide_count']} objetos com title (até 70 caracteres) e body "
            "(até 160 caracteres). Primeira página é um gancho forte, intermediárias "
            "oferecem dicas distintas, última página pede para salvar. "
            "Não use markdown, emojis, preços, estatísticas ou URLs inventadas. "
            "Não invente nomes de sites, marcas, produtos nem alegações. "
            "Se o tema pedir ferramentas e não houver lista de fontes, trate de "
            "critérios gerais e peça para o usuário pesquisar. "
            "Se existirem itens fornecidos, use apenas esses nomes e informações. "
            f"Tema: {req['topic']}. Itens confirmados pelo usuário: "
            f"{json.dumps(facts, ensure_ascii=False)}. Marca: {req['brand']}."
        )
        for _ in range(3):
            payload = json.dumps({
                "model": OLLAMA_MODEL, "prompt": prompt, "format": "json",
                "stream": False, "options": {"temperature": .25, "num_predict": 1400},
            }).encode("utf-8")
            request = Request(
                "http://127.0.0.1:11434/api/generate", data=payload,
                headers={"Content-Type": "application/json"})
            try:
                with urlopen(request, timeout=360) as response:
                    generated = json.loads(json.load(response)["response"])
                candidate = validate_request({
                    **req, "slides": generated["slides"]
                })["slides"]
                if len(candidate) == req["slide_count"]:
                    return candidate
            except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError):
                continue
        raise CarouselError("Ollama não gerou páginas válidas; forneça slides explicitamente")
    finally:
        if started:
            subprocess.run(["docker", "stop", "moneyprint-ollama"],
                           check=False, capture_output=True)


def render_one(path, output, env):
    path = Path(path)
    if path.stat().st_size > 32768:
        raise CarouselError("Pedido JSON excede 32 KiB")
    req = validate_request(json.loads(path.read_text(encoding="utf-8")))
    dest = output / path.stem
    dest.mkdir(parents=True, exist_ok=True)
    if not req["slides"]:
        req["slides"] = _generate_slides_with_local_llm(req)
    cache = Path(env.get("CAROUSEL_CACHE_DIR", "/tmp/moneyprint-carousel-cache"))
    candidates = search_free_photos(req["photo_terms"], req["source"], env, cache,
                                    photo_id=req["photo_id"])
    desired = 1 if req["photo_mode"] == "same" else len(req["only_pages"])
    chosen, files = [], []
    try:
        for candidate in candidates:
            if len(files) >= desired:
                break
            target = dest / ("_working_" + str(len(files)) + ".jpg")
            try:
                download_photo(candidate, target)
                # Decoder verified in download_photo; normalize independently in _cover.
                chosen.append(candidate)
                files.append(target)
            except (OSError, PhotoError, ValueError):
                target.unlink(missing_ok=True)
                continue
        if not files:
            raise PhotoError("As fotos encontradas não puderam ser baixadas")
        if req["photo_mode"] == "varied" and len(files) < desired:
            raise PhotoError("Fotos distintas insuficientes; tente photo_mode=same")
        if req["photo_mode"] == "same":
            return compose_carousel(req, files[0], dest, chosen[0])
        outpaths = []
        for asset_index, page_number in enumerate(req["only_pages"]):
            slide = req["slides"][page_number - 1]
            bg = _cover(files[asset_index], req["aspect"])
            target = dest / f"{page_number:02d}.jpg"
            _make_page(bg, slide, req, page_number, req["slide_count"]).save(
                target, format="JPEG", quality=91, optimize=True, subsampling=0)
            outpaths.append(target)
        _deliver(req, dest, outpaths, chosen)
        return outpaths
    finally:
        for photo in files:
            photo.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manual", default=os.getenv("REQUEST_PATH", ""))
    parser.add_argument("--before", default=os.getenv("PUSH_BEFORE", ""))
    parser.add_argument("--after", default=os.getenv("PUSH_AFTER", ""))
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    output = root / "carousel_outputs"
    try:
        requests = select_requests(root, manual=args.manual,
                                   before=args.before, after=args.after)
        for req_path in requests:
            print("Carrossel solicitado:", req_path.name, flush=True)
            try:
                rendered = render_one(req_path, output, os.environ)
                print("Carrossel renderizado:", len(rendered), "imagens", flush=True)
            except Exception as exc:
                dest = output / req_path.stem
                dest.mkdir(parents=True, exist_ok=True)
                (dest / "erro.txt").write_text(
                    f"{type(exc).__name__}: {exc}", encoding="utf-8")
                raise
        return 0
    except Exception as exc:
        print(f"Erro ao gerar carrossel: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
