"""Editorial vertical short (9:16): light grid background, bold sans + serif-italic accent,
white cards, dashed slots, drawn connectors. Everything is animated frame by frame with Skia
(true vector anti-aliasing, easing, blurred shadows), so beats can do things ASS cannot.

    python -m scripts.editorial_short --manifest requests/<x>.promo.json --out outputs/promo

Each section in the manifest carries ``beats``: ``{"at": "<word in the narration>", "kind": ..., ...}``.
A beat starts when that word is spoken (timing comes from the real audio) and lasts until the next one.
"""
from __future__ import annotations

import argparse
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import skia

from . import promo_build as P
from . import quality

W, H, FPS = 1080, 1920, 30
INK = (24, 22, 20)
MUTED = (112, 112, 118)
ORANGE = (232, 96, 44)
RED = (226, 54, 54)
GREEN = (44, 160, 96)
WHITE = (255, 255, 255)

_FONT_FILES = {
    "sans": "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf",
    "sansb": "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
    "sansm": "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf",
    "serif": "/usr/share/fonts/truetype/google-fonts/Lora-Italic-Variable.ttf",
}
_tf: dict[str, skia.Typeface] = {}


def font(kind: str, size: float) -> skia.Font:
    if kind not in _tf:
        tf = skia.Typeface.MakeFromFile(_FONT_FILES[kind]) if Path(_FONT_FILES[kind]).exists() else None
        _tf[kind] = tf or skia.Typeface.MakeDefault()
    f = skia.Font(_tf[kind], size)
    f.setSubpixel(True)
    return f


# ------------------------------------------------------------------ easing
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def out_cubic(x):
    return 1 - (1 - clamp(x)) ** 3


def out_back(x, s=1.70158):
    x = clamp(x) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def in_out(x):
    x = clamp(x)
    return 3 * x * x - 2 * x ** 3


def prog(t, t0, dur):
    return clamp((t - t0) / dur) if dur > 0 else (1.0 if t >= t0 else 0.0)


def col(rgb, a=1.0):
    return skia.Color4f(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, clamp(a))


def paint(rgb, a=1.0, style=None, width=None, blur=0.0, dash=None):
    p = skia.Paint(AntiAlias=True)
    p.setColor4f(col(rgb, a))
    if style == "stroke":
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(width or 2)
        p.setStrokeCap(skia.Paint.kRound_Cap)
        p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if dash:
        p.setPathEffect(skia.DashPathEffect.Make(dash, 0))
    return p


# ------------------------------------------------------------------ drawing primitives
def text(c: skia.Canvas, s: str, x, y, kind="sans", size=60, color=INK, a=1.0, align="center", scale=1.0, dy=0.0):
    f = font(kind, size)
    w = f.measureText(s)
    ox = x - (w / 2 if align == "center" else (w if align == "right" else 0))
    c.save()
    c.translate(x, y + dy)
    c.scale(scale, scale)
    c.translate(-x, -y)
    c.drawString(s, ox, y, f, paint(color, a))
    c.restore()
    return w


def rich(c, segs, x, y, kind="sans", size=60, a=1.0, scale=1.0, dy=0.0):
    """Centred line made of (text, colour) segments."""
    f = font(kind, size)
    widths = [f.measureText(s) for s, _ in segs]
    total = sum(widths)
    c.save()
    c.translate(x, y + dy)
    c.scale(scale, scale)
    c.translate(-x, -y)
    cx = x - total / 2
    for (s, colr), w in zip(segs, widths):
        c.drawString(s, cx, y, f, paint(colr, a))
        cx += w
    c.restore()


def fit_size(s: str, kind: str, size: float, max_w: float) -> float:
    w = font(kind, size).measureText(s)
    return size * max_w / w if w > max_w else size


def rrect(c, x, y, w, h, r, fill=WHITE, a=1.0, shadow=True, stroke=None, stroke_w=3, dash=None, scale=1.0):
    c.save()
    cx, cy = x + w / 2, y + h / 2
    c.translate(cx, cy)
    c.scale(scale, scale)
    c.translate(-cx, -cy)
    rect = skia.Rect.MakeXYWH(x, y, w, h)
    if shadow:
        c.drawRoundRect(skia.Rect.MakeXYWH(x + 2, y + 16, w - 4, h), r, r, paint((20, 24, 40), 0.14 * a, blur=22))
    if fill is not None:
        c.drawRoundRect(rect, r, r, paint(fill, a))
    if stroke:
        c.drawRoundRect(rect, r, r, paint(stroke, a, "stroke", stroke_w, dash=dash))
    c.restore()


def tile(c, x, y, size, letter, color=ORANGE, a=1.0, scale=1.0):
    """App-icon style tile: white rounded square with a monogram."""
    rrect(c, x - size / 2, y - size / 2, size, size, size * 0.24, WHITE, a, scale=scale)
    c.save()
    c.translate(x, y)
    c.scale(scale, scale)
    c.translate(-x, -y)
    f = font("sans", size * 0.54)
    w = f.measureText(letter)
    c.drawString(letter, x - w / 2, y + size * 0.19, f, paint(color, a))
    c.restore()


def check(c, x, y, r, p, color=GREEN, a=1.0):
    path = skia.Path()
    pts = [(x - r * 0.5, y + r * 0.05), (x - r * 0.12, y + r * 0.42), (x + r * 0.55, y - r * 0.38)]
    path.moveTo(*pts[0]); path.lineTo(*pts[1]); path.lineTo(*pts[2])
    dst = skia.Path()
    pm = skia.PathMeasure(path, False)
    pm.getSegment(0, pm.getLength() * clamp(p), dst, True)
    c.drawCircle(x, y, r, paint(color, 0.14 * a))
    c.drawPath(dst, paint(color, a, "stroke", r * 0.22))


def line(c, x1, y1, x2, y2, p, color=INK, a=1.0, width=4):
    c.drawLine(x1, y1, x1 + (x2 - x1) * clamp(p), y1 + (y2 - y1) * clamp(p), paint(color, a, "stroke", width))


def plus(c, x, y, r, color, a=1.0):
    c.drawLine(x - r, y, x + r, y, paint(color, a, "stroke", 5))
    c.drawLine(x, y - r, x, y + r, paint(color, a, "stroke", 5))


def lock(c, x, y, s, color=INK, a=1.0):
    c.drawRoundRect(skia.Rect.MakeXYWH(x - s * 0.5, y - s * 0.1, s, s * 0.75), s * 0.14, s * 0.14, paint(color, a))
    sh = skia.Path()
    sh.addArc(skia.Rect.MakeXYWH(x - s * 0.32, y - s * 0.62, s * 0.64, s * 0.8), 180, 180)
    c.drawPath(sh, paint(color, a, "stroke", s * 0.14))


# ------------------------------------------------------------------ background
class Background:
    def __init__(self):
        surf = skia.Surface(W, H)
        c = surf.getCanvas()
        c.clear(skia.ColorSetRGB(244, 245, 247))
        gp = paint((222, 225, 231), 1.0, "stroke", 2)
        for x in range(0, W + 1, 60):
            c.drawLine(x, 0, x, H, gp)
        for y in range(0, H + 1, 60):
            c.drawLine(0, y, W, y, gp)
        self.img = surf.makeImageSnapshot()

    def draw(self, c, t):
        c.drawImage(self.img, 0, 0)
        for i, (bx, by, r, ca) in enumerate([(220, 420, 320, 0.55), (900, 1050, 360, 0.5), (300, 1600, 330, 0.45)]):
            x = bx + 40 * math.sin(t * 0.35 + i * 2.1)
            y = by + 50 * math.cos(t * 0.28 + i)
            c.drawCircle(x, y, r, paint((236, 238, 242), ca, blur=95))
            c.drawCircle(x + 200, y - 160, r * 0.5, paint((255, 214, 190), 0.30, blur=110))


# ------------------------------------------------------------------ beats
# Every beat gets: c, t (seconds since the beat started), d (beat duration), p (params dict)
def beat_alpha(t, d):
    return out_cubic(prog(t, 0, 0.25)) * (1 - in_out(prog(t, d - 0.3, 0.2)))


def hero(c, t, d, p):
    a = beat_alpha(t, d)
    y = 640
    lines = p["lines"]
    for i, ln in enumerate(lines):
        k = prog(t, 0.05 + 0.1 * i, 0.5)
        size = fit_size(ln, "sans", 118, 820)
        text(c, ln, W / 2, y + i * 140, "sans", size, INK, a * out_cubic(k), dy=(1 - out_cubic(k)) * 46)
    if p.get("serif"):
        k = prog(t, 0.2 + 0.1 * len(lines), 0.55)
        size = fit_size(p["serif"], "serif", 92, 820)
        text(c, p["serif"], W / 2, y + len(lines) * 140 + 30, "serif", size, ORANGE, a * out_cubic(k),
             dy=(1 - out_cubic(k)) * 36)
    vis = p.get("visual")
    if vis == "price":
        k = prog(t, 0.7, 0.5)
        yy = 1010
        rrect(c, 190, yy, 700, 190, 40, WHITE, a * out_cubic(k), scale=0.92 + 0.08 * out_back(k))
        text(c, p.get("price", "R$ ??? /mês"), W / 2, yy + 118, "sans", 84, INK, a * out_cubic(k))
        s = prog(t, 1.3, 0.45)
        if s > 0:
            c.drawLine(230, yy + 98, 230 + 620 * out_cubic(s), yy + 98, paint(RED, a, "stroke", 12))
    elif vis == "bubbles":
        for i, (s_, x) in enumerate(zip(p["bubbles"], [300, 760, 400])):
            k = prog(t, 0.7 + 0.45 * i, 0.5)
            w_ = font("sansb", 44).measureText(s_) + 90
            yy = 1010 + i * 150
            xx = x - w_ / 2 if i % 2 == 0 else 880 - w_
            rrect(c, xx, yy, w_, 104, 52, WHITE if i % 2 == 0 else ORANGE, a * out_cubic(k), scale=0.9 + 0.1 * out_back(k))
            text(c, s_, xx + w_ / 2, yy + 68, "sansb", 44, INK if i % 2 == 0 else WHITE, a * out_cubic(k))


def slots(c, t, d, p):
    a = beat_alpha(t, d)
    cx, cy = W / 2, 930
    k = prog(t, 0, 0.55)
    corners = [(-300, -250), (300, -250), (-300, 250), (300, 250)]
    labels = p.get("slots", ["", "", "", ""])
    for i, (dx, dy) in enumerate(corners):
        kk = prog(t, 0.35 + 0.3 * i, 0.5)
        dash = [16, 12]
        rrect(c, cx + dx - 70, cy + dy - 70, 140, 140, 28, None, a * out_cubic(k), shadow=False, stroke=ORANGE, stroke_w=4, dash=dash)
        if kk <= 0.05:
            plus(c, cx + dx, cy + dy, 24, ORANGE, a * out_cubic(k))
        else:
            rrect(c, cx + dx - 70, cy + dy - 70, 140, 140, 28, WHITE, a * out_cubic(kk), scale=0.85 + 0.15 * out_back(kk))
            text(c, labels[i][:1].upper(), cx + dx, cy + dy + 22, "sans", 66, ORANGE, a * out_cubic(kk))
            text(c, labels[i], cx + dx, cy + dy + 118, "sansb", 34, INK, a * out_cubic(kk))
    tile(c, cx, cy, 250, p.get("letter", "P"), ORANGE, a * out_cubic(k), scale=0.8 + 0.2 * out_back(k))
    if p.get("caption"):
        text(c, p["caption"], W / 2, 1340, "serif", 64, ORANGE, a * out_cubic(prog(t, 1.4, 0.5)))


def stack(c, t, d, p):
    a = beat_alpha(t, d)
    items = p["items"]
    x0, w_, h_ = 120, 840, 140
    y0 = 560 if p.get("title") is None else 760
    if p.get("title"):
        text(c, p["title"], W / 2, 640, "sans", fit_size(p["title"], "sans", 96, 820), INK, a * out_cubic(prog(t, 0, 0.4)))
        if p.get("serif"):
            text(c, p["serif"], W / 2, 740, "serif", 64, ORANGE, a * out_cubic(prog(t, 0.15, 0.4)))
            y0 = 840
    for i, it in enumerate(items):
        k = prog(t, 0.3 + 0.38 * i, 0.5)
        yy = y0 + i * (h_ + 34)
        ox = (1 - out_cubic(k)) * 420
        rrect(c, x0 + ox, yy, w_, h_, 34, WHITE, a * out_cubic(k))
        c.drawCircle(x0 + ox + 78, yy + h_ / 2, 34, paint(ORANGE, 0.12 * a * out_cubic(k)))
        text(c, str(i + 1), x0 + ox + 78, yy + h_ / 2 + 17, "sans", 46, ORANGE, a * out_cubic(k))
        text(c, it[0], x0 + ox + 142, yy + h_ / 2 + 17, "sansb", fit_size(it[0], "sansb", 50, w_ - 142 - 120), INK, a * out_cubic(k), align="left")
        if len(it) > 1:
            text(c, it[1], x0 + ox + w_ - 150, yy + h_ / 2 + 14, "sansm", 32, MUTED, a * out_cubic(k), align="right")
        check(c, x0 + ox + w_ - 70, yy + h_ / 2, 30, prog(t, 0.3 + 0.38 * i + 0.45, 0.35), GREEN, a * out_cubic(k))


def flow(c, t, d, p):
    a = beat_alpha(t, d)
    nodes = p["nodes"]
    if p.get("title"):
        text(c, p["title"], W / 2, 620, "sans", fit_size(p["title"], "sans", 92, 820), INK, a * out_cubic(prog(t, 0, 0.4)))
    w_, h_ = 700, 130
    x0 = (W - w_) / 2
    y0 = 760
    gap = 80
    for i, nd in enumerate(nodes):
        k = prog(t, 0.2 + 0.55 * i, 0.5)
        yy = y0 + i * (h_ + gap)
        sc = 0.88 + 0.12 * out_back(k)
        rrect(c, x0, yy, w_, h_, 36, WHITE, a * out_cubic(k), scale=sc, stroke=ORANGE if i == len(nodes) - 1 else None)
        c.drawCircle(x0 + 88, yy + h_ / 2, 40, paint(ORANGE, 0.13 * a * out_cubic(k)))
        text(c, nd[:1].upper(), x0 + 88, yy + h_ / 2 + 18, "sans", 52, ORANGE, a * out_cubic(k))
        text(c, nd, x0 + 160, yy + h_ / 2 + 17, "sansb", 50, INK, a * out_cubic(k), align="left")
        if i < len(nodes) - 1:
            lp = prog(t, 0.2 + 0.55 * i + 0.4, 0.4)
            line(c, W / 2, yy + h_, W / 2, yy + h_ + gap, lp, INK, a, 5)
            if lp >= 1:      # travelling dot along the connector
                tt = ((t - (0.2 + 0.55 * i + 0.8)) * 0.9) % 1
                c.drawCircle(W / 2, yy + h_ + gap * tt, 11, paint(ORANGE, a))


def search(c, t, d, p):
    a = beat_alpha(t, d)
    x0, w_ = 100, 880
    k = prog(t, 0, 0.45)
    rrect(c, x0, 640, w_, 130, 65, WHITE, a * out_cubic(k), scale=0.92 + 0.08 * out_back(k))
    c.drawCircle(x0 + 80, 705, 22, paint(MUTED, a * out_cubic(k), "stroke", 5))
    c.drawLine(x0 + 96, 721, x0 + 116, 741, paint(MUTED, a * out_cubic(k), "stroke", 5))
    typed, fixed = p["typed"], p["fixed"]
    n = int(len(typed) * prog(t, 0.5, 1.0))
    shown = typed[:n] if prog(t, 1.9, 0.1) < 1 else fixed
    text(c, shown + ("|" if int(t * 2) % 2 == 0 and prog(t, 1.9, 0.1) < 1 else ""), x0 + 150, 718, "sansb", 54, INK, a, align="left")
    if prog(t, 1.9, 0.1) >= 1:
        k2 = prog(t, 1.9, 0.4)
        rrect(c, x0 + w_ - 330, 800, 330, 76, 38, GREEN, a * out_cubic(k2), shadow=False, scale=0.9 + 0.1 * out_back(k2))
        text(c, p.get("pill", "erro perdoado"), x0 + w_ - 165, 851, "sansb", 34, WHITE, a * out_cubic(k2))
    for i, r_ in enumerate(p["results"]):
        kk = prog(t, 1.2 + 0.3 * i + (0.9 if i == 0 else 0.9), 0.45)
        yy = 920 + i * 150
        ox = (1 - out_cubic(kk)) * 140
        rrect(c, x0, yy + ox, w_, 126, 30, WHITE, a * out_cubic(kk))
        c.drawRoundRect(skia.Rect.MakeXYWH(x0 + 28, yy + ox + 28, 70, 70), 16, 16, paint(ORANGE, 0.14 * a * out_cubic(kk)))
        text(c, r_, x0 + 130, yy + ox + 82, "sansb", 46, INK, a * out_cubic(kk), align="left")


def alert(c, t, d, p):
    a = beat_alpha(t, d)
    k = prog(t, 0, 0.5)
    shake = math.sin(t * 40) * 6 * (1 - prog(t, 0.5, 0.5)) * (1 if k >= 1 else 0)
    w_, h_ = 880, 150
    x = (W - w_) / 2 + shake
    rrect(c, x, 700, w_, h_, 40, WHITE, a * out_cubic(k), stroke=RED, stroke_w=5, scale=0.9 + 0.1 * out_back(k))
    c.drawCircle(x + 80, 775, 34, paint(RED, a * out_cubic(k)))
    text(c, "!", x + 80, 794, "sans", 54, WHITE, a * out_cubic(k))
    text(c, p["text"], x + 140, 790, "sansb", fit_size(p["text"], "sansb", 48, w_ - 190), RED, a * out_cubic(k), align="left")
    if p.get("title"):
        kk = prog(t, 0.5, 0.5)
        text(c, p["title"], W / 2, 1010, "sans", fit_size(p["title"], "sans", 100, 820), INK, a * out_cubic(kk), dy=(1 - out_cubic(kk)) * 40)
    if p.get("serif"):
        kk = prog(t, 0.7, 0.5)
        text(c, p["serif"], W / 2, 1120, "serif", 80, ORANGE, a * out_cubic(kk), dy=(1 - out_cubic(kk)) * 30)


def vault(c, t, d, p):
    a = beat_alpha(t, d)
    k = prog(t, 0, 0.5)
    rrect(c, 100, 600, 880, 130, 36, WHITE, a * out_cubic(k), scale=0.92 + 0.08 * out_back(k))
    lock(c, 190, 668, 54, INK, a * out_cubic(k))
    text(c, p.get("name", "cofre de segredos"), 250, 683, "sansb", 48, INK, a * out_cubic(k), align="left")
    for i, (key, who) in enumerate(p["secrets"]):
        kk = prog(t, 0.5 + 0.4 * i, 0.5)
        yy = 780 + i * 150
        rrect(c, 100, yy, 880, 126, 30, WHITE, a * out_cubic(kk), scale=0.94 + 0.06 * out_back(kk))
        text(c, key, 140, yy + 76, "sansb", 40, INK, a * out_cubic(kk), align="left")
        text(c, "•••••••", 520, yy + 76, "sansm", 40, MUTED, a * out_cubic(kk), align="left")
        rrect(c, 780, yy + 32, 160, 62, 31, ORANGE, a * out_cubic(kk) * 0.14, shadow=False)
        text(c, who, 860, yy + 76, "sansb", 30, ORANGE, a * out_cubic(kk))


def cta(c, t, d, p):
    a = beat_alpha(t, d) if d < 99 else out_cubic(prog(t, 0, 0.3))
    for i, ln in enumerate(p["lines"]):
        k = prog(t, 0.1 + 0.15 * i, 0.5)
        text(c, ln, W / 2, 760 + i * 150, "sans", fit_size(ln, "sans", 130, 820), INK, a * out_cubic(k), scale=0.85 + 0.15 * out_back(k))
    if p.get("serif"):
        k = prog(t, 0.5, 0.5)
        text(c, p["serif"], W / 2, 760 + len(p["lines"]) * 150 + 30, "serif", fit_size(p["serif"], "serif", 84, 820), ORANGE, a * out_cubic(k))
    if p.get("handle"):
        k = prog(t, 0.9, 0.5)
        rrect(c, 290, 1180, 500, 120, 60, ORANGE, a * out_cubic(k), scale=0.9 + 0.1 * out_back(k))
        text(c, p["handle"], W / 2, 1258, "sans", 52, WHITE, a * out_cubic(k))


BEATS = {"hero": hero, "slots": slots, "stack": stack, "flow": flow, "search": search, "alert": alert,
         "vault": vault, "cta": cta}


# ------------------------------------------------------------------ timeline
def anchor_times(narration: str, words, beats):
    """Resolve each beat's ``at`` (a word) to the time that word starts, searching forward."""
    norm = lambda s: "".join(ch for ch in s.lower() if ch.isalnum())
    out, cursor = [], 0
    for b in beats:
        target = norm(b.get("at", ""))
        t = None
        if target:
            for i in range(cursor, len(words)):
                if norm(words[i][0]) == target:
                    t, cursor = words[i][1], i
                    break
        out.append(0.0 if t is None and not out else (t if t is not None else out[-1]))
    return out


def draw_chapter(c, t, dur, sec, idx, n, starts, bg: Background, hdr_t):
    bg.draw(c, t)
    # persistent header: ordinal label + tool name tile
    k = out_cubic(prog(t, 0.05, 0.5))
    text(c, f"{idx + 1}ª ferramenta", W / 2, 250, "serif", 44, MUTED, k)
    tile(c, W / 2 - font("sans", 58).measureText(sec["title"]) / 2 - 56, 345, 84, sec["title"][:1].upper(), ORANGE, k, scale=0.8 + 0.2 * out_back(prog(t, 0.05, 0.5)))
    text(c, sec["title"], W / 2 + 30, 366, "sans", 58, INK, k, dy=(1 - k) * 14)
    # active beat
    beats = sec["beats"]
    active = max((i for i, s in enumerate(starts) if t >= s), default=0)
    s0 = starts[active]
    e0 = starts[active + 1] if active + 1 < len(beats) else 1e9
    b = beats[active]
    c.save()
    c.translate(W / 2, 560)       # fill the screen better: scale about the top of the content area, nudge down
    c.scale(1.15, 1.15)
    c.translate(-W / 2, -560 + 105)
    BEATS[b["kind"]](c, t - s0, min(e0 - s0, 99), b)
    c.restore()


def easing_slide(x):
    return in_out(x)


def render(manifest, secs, work: Path, out: Path) -> Path:
    work.mkdir(parents=True, exist_ok=True)
    bg = Background()
    durs, voices, bstarts, wtimes = [], [], [], []
    for i, sec in enumerate(secs):
        v = work / f"voice{i}.wav"
        d = P.prepare_voice(sec["voice"], v)
        iv = P.speech_intervals(v, d)
        words = P.word_times(sec["narration"], iv)
        bstarts.append(anchor_times(sec["narration"], words, sec["beats"]))
        durs.append(d); voices.append(v)
    outro_d = P.OUTRO_S + 0.6
    cdurs = durs + [outro_d]
    starts, total = P.timeline(cdurs)
    n = len(secs)

    surf = skia.Surface(W, H)
    csurf = [skia.Surface(W, H), skia.Surface(W, H)]
    arr = np.empty((H, W, 4), np.uint8)
    info = skia.ImageInfo.Make(W, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType)
    out.mkdir(parents=True, exist_ok=True)
    final = out / "short_editorial_9x16.mp4"

    # audio: voices delayed to their chapter start + a whoosh per transition
    inputs, fc = [], []
    for i, v in enumerate(voices):
        inputs += ["-i", v]
        ms = int(starts[i] * 1000)
        fc.append(f"[{i}:a]aformat=channel_layouts=stereo,adelay={ms}|{ms}[a{i}]")
    w_in, w_f, w_lab = P.whoosh_inputs([starts[k] - 0.05 for k in range(1, n + 1)])
    w_f = [f.replace(f"{{n{i}}}", str(n + 1 + i)) for i, f in enumerate(w_f)]
    inputs = ["-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"] + inputs
    # shift indexes: video pipe is input 0
    fc = [f.replace(f"[{i}:a]", f"[{i + 1}:a]") for i, f in enumerate(fc)]
    mix_in = "".join(f"[a{i}]" for i in range(n))
    fc += w_f
    fc.append(f"{mix_in}{w_lab}amix=inputs={n + len(w_f)}:duration=longest:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[aout]")
    cmd = ["ffmpeg", "-loglevel", "error", "-y", *inputs, *w_in, "-filter_complex", ";".join(fc),
           "-map", "0:v", "-map", "[aout]", "-vf", "format=yuv420p", *quality.x264_args(threads=2),
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{total:.3f}", "-movflags", "+faststart", str(final)]
    cmd = [str(x) for x in cmd]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    frames = int(total * FPS)
    for fi in range(frames):
        t = fi / FPS
        # chapters active at t (1 or 2 during a crossfade)
        act = [i for i in range(n + 1) if starts[i] <= t < starts[i] + cdurs[i]]
        cvs = []
        for slot, i in enumerate(act):
            cs = csurf[slot]
            cc = cs.getCanvas()
            lt = t - starts[i]
            if i < n:
                draw_chapter(cc, lt, cdurs[i], secs[i], i, n, bstarts[i], bg, lt)
            else:
                bg.draw(cc, t)
                cta(cc, lt, 99, manifest_cta(manifest))
            cvs.append((i, cs))
        c = surf.getCanvas()
        if len(cvs) == 1:
            c.drawImage(cvs[0][1].makeImageSnapshot(), 0, 0)
        else:   # slide transition between the two chapters
            (ia, sa), (ib, sb) = cvs
            k = in_out((t - starts[ib]) / P.XF)
            c.drawImage(sa.makeImageSnapshot(), -W * k, 0)
            c.drawImage(sb.makeImageSnapshot(), W * (1 - k), 0)
        # progress bar
        c.drawRect(skia.Rect.MakeXYWH(0, 0, W * t / total, 10), paint(ORANGE))
        surf.readPixels(info, arr, W * 4)
        proc.stdin.write(arr.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg failed")
    return final


def manifest_cta(manifest):
    o = manifest["outro"]
    return {"lines": o["title"], "serif": " ".join(o["subtitle"]), "handle": manifest["handle"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=P.REPO / "outputs" / "promo")
    ap.add_argument("--work", type=Path, default=None)
    ap.add_argument("--only", type=int, default=None, help="render only this section index (preview)")
    args = ap.parse_args(argv)
    manifest, _req, secs = P.load(args.manifest if args.manifest.is_absolute() else P.REPO / args.manifest)
    if args.only is not None:
        secs = [secs[args.only]]
    final = render(manifest, secs, args.work or args.out / "_work_editorial", args.out)
    print(final, f"{P.probe(final):.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
