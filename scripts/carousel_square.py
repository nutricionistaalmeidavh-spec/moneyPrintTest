"""1080×1080 carousel overlays for real photos, deterministic and free.

The same source image is composited by render_carousel for each page; this module
never fetches media, generates AI images, or posts to social networks.
"""
from PIL import Image, ImageDraw
from scripts.render_carousel import CarouselError, _get_font

SIZE = 1080
INK = (11, 13, 22)
PURPLE = (183, 71, 249)


def _font(draw, text, max_width, start=66, minimum=26, bold=True):
    for px in range(start, minimum - 1, -2):
        ft = _get_font(px, bold=bold)
        if draw.textbbox((0, 0), text, font=ft)[2] <= max_width:
            return ft, px
    raise CarouselError("Texto longo demais para a imagem quadrada")


def _wrap(draw, text, max_width, start=52, minimum=29, max_lines=4, bold=False):
    for px in range(start, minimum - 1, -2):
        ft = _get_font(px, bold=bold)
        lines, current = [], ""
        for word in text.split():
            proposed = (current + " " + word).strip()
            if draw.textbbox((0, 0), proposed, font=ft)[2] <= max_width:
                current = proposed
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        if len(lines) <= max_lines and all(
            draw.textbbox((0, 0), ln, font=ft)[2] <= max_width
            for ln in lines
        ):
            return ft, px, lines
    raise CarouselError("Descrição longa demais para o formato quadrado")


def _brush(draw, text, center, y, max_width=920, font_size=74):
    ft, px = _font(draw, text, max_width - 75, font_size)
    text_w = draw.textbbox((0, 0), text, font=ft)[2]
    half = text_w // 2 + 34
    left, right = max(40, center - half), min(SIZE - 40, center + half)
    top, bottom = y - (px + 37) // 2, y + (px + 37) // 2
    polygon = [(left + 12, top + 5)]
    for x in range(left + 12, right - 10, 23):
        polygon.append((x, top + (x * 7 % 13) - 4))
    polygon += [(right + 10, top + 15), (right - 4, bottom - 6)]
    for x in range(right - 4, left + 6, -21):
        polygon.append((x, bottom + (x * 3 % 9) - 3))
    polygon += [(left - 10, bottom - 14), (left - 4, top + 10)]
    draw.polygon([(x + 3, z + 5) for x, z in polygon],
                 fill=(12, 13, 29, 210))
    draw.polygon(polygon, fill="white")
    draw.text((center, y - 2), text, font=ft, anchor="mm", fill=INK)
    return top, bottom


def _label(draw, text, center_y=440):
    ft, px = _font(draw, text, 850, 54)
    tw = draw.textbbox((0, 0), text, font=ft)[2]
    left = (SIZE - tw - 88) // 2
    right = SIZE - left
    draw.rounded_rectangle((left, center_y - 38, right, center_y + 45),
                           radius=31, fill=(8, 14, 34, 242),
                           outline=PURPLE, width=4)
    draw.text((SIZE // 2, center_y), text, anchor="mm", font=ft,
              fill="white")


def _body(draw, content, y0=610, y1=810):
    draw.rounded_rectangle((75, y0, 1005, y1), radius=36,
                           fill=(4, 10, 25, 223))
    ft, px, lines = _wrap(draw, content, 818, 55, max_lines=4)
    step = round(px * 1.24)
    y = (y0 + y1) // 2 - step * (len(lines) - 1) // 2
    for line in lines:
        draw.text((SIZE // 2, y), line, anchor="mm", fill="white", font=ft)
        y += step


def _pill(draw, text, y=905, dark=False):
    if not text:
        return
    ft, px = _font(draw, text, 790, 45)
    width = min(925, max(420, draw.textbbox((0, 0), text, font=ft)[2] + 90))
    left = (SIZE - width) // 2
    draw.rounded_rectangle((left + 2, y + 6, left + width + 2, y + 88),
                           radius=43, fill=(7, 8, 24, 195))
    draw.rounded_rectangle((left, y, left + width, y + 83),
                           radius=43,
                           fill=(89, 22, 164) if dark else "white",
                           outline=(216, 120, 255) if dark else "white",
                           width=2)
    draw.text((SIZE // 2, y + 39), text, font=ft,
              anchor="mm", fill="white" if dark else INK)


def make_square_editorial_page(background, slide, req, index, total):
    """One visual template, one intact setup photograph, all pages 1080x1080."""
    if background.size != (SIZE, SIZE):
        raise CarouselError("Editorial quadrado precisa de fundo 1080×1080")
    image = background.convert("RGBA")
    overlay = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    shade = ImageDraw.Draw(overlay)
    for y in range(160, SIZE):
        p = (y - 160) / (SIZE - 160)
        alpha = int(12 + 190 * p ** 1.15)
        shade.line((0, y, SIZE, y), fill=(5, 8, 19, alpha))
    image = Image.alpha_composite(image, overlay)
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((35, 32, 188, 77), radius=22,
                           fill=(6, 11, 29, 211))
    draw.text((112, 55), req.get("brand", "ArtiSys").upper(),
              font=_get_font(22), fill="white", anchor="mm")
    draw.text((1031, 56), f"{index}/{total}",
              font=_get_font(25), fill="white", anchor="rm")
    if index == 1:
        title = slide["title"].upper()
        # Break title intentionally into readable brush strokes.
        ft, px, lines = _wrap(draw, title, 860, 74, 40,
                              max_lines=3, bold=True)
        y = 200 if len(lines) > 1 else 250
        for line in lines:
            _brush(draw, line, SIZE // 2, y, font_size=px)
            y += 100
        hl = slide.get("highlight", "")
        if hl and hl.upper() not in title:
            _brush(draw, hl.upper(), SIZE // 2, y + 2, font_size=76)
        body = slide.get("body", "")
        if body:
            draw.rounded_rectangle((138, 580, 942, 671), radius=43,
                                   fill=(8, 12, 28, 214))
            f, _ = _font(draw, body, 755, 59, bold=False)
            draw.text((SIZE // 2, 624), body, font=f, anchor="mm", fill="white")
        f, _ = _font(draw, "›››››››››", 720, 99)
        draw.text((SIZE // 2, 825), "›››››››››", font=f,
                  anchor="mm", fill="white")
        draw.text((SIZE // 2, 989), "DESLIZE PARA CONHECER",
                  font=_get_font(25), anchor="mm", fill=(226, 232, 246))
    elif index == total:
        _brush(draw, slide["title"], SIZE // 2, 220, font_size=78)
        _brush(draw, slide.get("highlight") or "PRA TESTAR DEPOIS",
               SIZE // 2, 350, font_size=65)
        _body(draw, slide.get("body", ""), 554, 791)
        _pill(draw, "SEGUE A ARTISYS", 905, dark=True)
    else:
        _brush(draw, slide["title"], SIZE // 2, 190, font_size=82)
        category = slide.get("highlight", "")
        if category:
            _label(draw, category.upper(), 441)
        _body(draw, slide.get("body", ""), 585, 803)
        _pill(draw, slide.get("url", ""), 900)
    return image.convert("RGB")
