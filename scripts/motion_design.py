"""Frame-accurate cosmic opener: zero-cost FFmpeg/Pillow or opt-in Three.js."""
from __future__ import annotations

import math
import random
import subprocess
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


def _font(size: int):
    for path in (
        "/usr/share/fonts/truetype/inter/Inter-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ):
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _universe_canvas(size: tuple[int, int], title: str) -> Image.Image:
    """Generate original high-res assets; no downloaded GIF or pixelated text."""
    w, h = size
    scale = 1.15
    sw, sh = math.ceil(w * scale), math.ceil(h * scale)
    background = Image.new("RGB", (sw, sh), (5, 8, 21))
    nebula = Image.new("RGBA", (sw, sh))
    painter = ImageDraw.Draw(nebula)
    painter.ellipse((sw*.12, sh*.01, sw*.89, sh*.94), fill=(30, 41, 102, 70))
    painter.ellipse((sw*.30, -sh*.15, sw*1.1, sh*.95), fill=(54, 29, 84, 42))
    painter.ellipse((sw*.05, sh*.40, sw*.72, sh*1.1), fill=(13, 86, 110, 37))
    background = Image.alpha_composite(background.convert("RGBA"),
                                       nebula.filter(ImageFilter.GaussianBlur(max(35, w//20))))
    stars = ImageDraw.Draw(background)
    rng = random.Random(8419)
    for i in range(max(160, w*h//4300)):
        x, y = rng.randrange(sw), rng.randrange(sh)
        size_star = 1 if i % 9 else 2
        strength = rng.randint(90, 230)
        stars.ellipse((x, y, x+size_star, y+size_star),
                      fill=(strength, strength, min(255, strength+16), 215))
    # Text rasterized at source resolution with TrueType, then camera zoom moves it.
    face = _font(max(30, round(w*.052)))
    label = title.strip()
    while len(label) > 2 and stars.textbbox((0, 0), label, font=face)[2] > sw*.86:
        size_now = getattr(face, "size", 36)
        face = _font(max(20, size_now-3))
    y = sh*.49
    shadows = Image.new("RGBA", (sw, sh))
    shadow = ImageDraw.Draw(shadows)
    shadow.text((sw/2, y+5), label, anchor="mm", font=face, fill=(0, 0, 0, 210))
    background = Image.alpha_composite(background,
                                       shadows.filter(ImageFilter.GaussianBlur(12)))
    stars = ImageDraw.Draw(background)
    stars.text((sw/2, y), label, anchor="mm", font=face, fill=(240, 245, 255, 255))
    return background.convert("RGB")


def render_universe(target: Path, *, title: str, seconds: float,
                    size: tuple[int, int], fps: int = 30) -> Path:
    if not (0 < seconds <= 8 and fps > 0 and all(x > 0 for x in size)):
        raise ValueError("Parâmetros da animação inválidos")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="moneyprint-space-") as folder:
        canvas = Path(folder) / "space.png"
        _universe_canvas(size, title).save(canvas)
        w, h = size
        frames = max(1, round(seconds * fps))
        # zoompan consumes one input image per output frame, giving smooth true FPS.
        effect = (f"zoompan=z='min(zoom+0.0007,1.07)':"
                  f"x='iw/2-(iw/zoom/2)+on*0.14':y='ih/2-(ih/zoom/2)':"
                  f"d=1:s={w}x{h}:fps={fps},format=yuv420p")
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
            "-loop", "1", "-framerate", str(fps), "-i", str(canvas),
            "-vf", effect, "-frames:v", str(frames), "-an",
            "-c:v", "libx264", "-crf", "19", "-preset", "veryfast",
            "-movflags", "+faststart", str(target),
        ], check=True, timeout=480)
    return target


def render_threejs_universe(target: Path, *, title: str, seconds: float,
                            size: tuple[int, int], fps: int = 30) -> Path:
    """Render local Three.js frames from a loopback-only web server."""
    project = Path(__file__).resolve().parent.parent / "motion" / "three-universe"
    if not (project / "node_modules" / "three" / "build" / "three.module.js").is_file():
        raise RuntimeError("P2: instale a dependência livre: npm ci --prefix motion/three-universe")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("P2: Playwright/Chromium requeridos para render 3D") from exc

    class LocalHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(project), **kwargs)
        def log_message(self, fmt, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), LocalHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="moneyprint-three-") as folder:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True, args=[
                    "--use-gl=angle", "--use-angle=swiftshader",
                    "--enable-unsafe-swiftshader", "--enable-webgl"])
                try:
                    w, h = size
                    page = browser.new_page(viewport={"width": w, "height": h},
                                            device_scale_factor=1)
                    page.goto(f"http://127.0.0.1:{server.server_port}/index.html",
                              wait_until="load", timeout=30000)
                    page.wait_for_function("typeof window.renderAt === 'function'",
                                           timeout=30000)
                    page.evaluate("(title) => document.querySelector('#headline').textContent = title",
                                  title)
                    frame_count = round(seconds * fps)
                    for n in range(frame_count):
                        page.evaluate("(t) => window.renderAt(t)", n / fps)
                        page.screenshot(path=str(Path(folder) / f"frame-{n:05d}.png"),
                                        animations="disabled")
                finally:
                    browser.close()
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                "-framerate", str(fps), "-i", str(Path(folder) / "frame-%05d.png"),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19",
                "-movflags", "+faststart", str(target)
            ], check=True, timeout=900)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    return target
