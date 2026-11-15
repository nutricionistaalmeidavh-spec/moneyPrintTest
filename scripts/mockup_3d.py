"""Optional 100% local Three.js device mockup renderer.

Requires npm install --prefix tools/mockup-catalog, Playwright Chromium and FFmpeg.
No paid service, external CDN or automatic package installation.
"""
from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import tempfile
from threading import Thread
from urllib.parse import urlencode

DEVICES = frozenset({"laptop", "monitor"})
MOTIONS = frozenset({"enter", "orbit", "zoom", "float"})
ASPECTS = frozenset({"16:9", "9:16", "1:1"})


def validate_mockup(device: str, motion: str, aspect: str) -> tuple[str, str, str]:
    if device not in DEVICES or motion not in MOTIONS or aspect not in ASPECTS:
        raise ValueError("Dispositivo, motion ou formato 3D inválido")
    return device, motion, aspect


def render_mockup(
    media: Path, output: Path, *, device: str = "laptop", motion: str = "enter",
    aspect: str = "16:9", fps: int = 30, frames: int = 120,
    width: int | None = None, height: int | None = None
) -> dict:
    validate_mockup(device, motion, aspect)
    if fps not in (24, 25, 30, 60) or not 1 <= frames <= fps * 3600:
        raise ValueError("FPS ou duração inválida")
    default = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}[aspect]
    width, height = width or default[0], height or default[1]
    if min(width, height) < 160 or width % 2 or height % 2:
        raise ValueError("Resolução deve ser par e pelo menos 160 px")
    media = Path(media).resolve()
    if not media.is_file() or media.suffix.lower() not in {".mp4", ".webm"}:
        raise ValueError("Gravação local MP4/WebM obrigatória")
    project_root = Path(__file__).resolve().parents[1]
    catalog = project_root / "tools" / "mockup-catalog"
    if not (catalog / "node_modules/three/build/three.module.js").is_file():
        raise RuntimeError("Instale Three.js localmente: npm install --prefix tools/mockup-catalog")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Instale Playwright e seu Chromium: pip install playwright; playwright install chromium") from exc

    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(catalog)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    query = urlencode({"render": "1", "device": device, "motion": motion})
    url = f"http://127.0.0.1:{server.server_port}/index.html?{query}"
    with tempfile.TemporaryDirectory(prefix="moneyprint_mockup_") as tmp:
        log_path = Path(tmp) / "ffmpeg.log"
        try:
            with log_path.open("wb") as log, sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True, args=[
                    "--no-sandbox", "--enable-webgl", "--use-gl=angle",
                    "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                ])
                try:
                    page = browser.new_page(viewport={"width": width, "height": height},
                                            device_scale_factor=1)
                    errors = []
                    page.on("pageerror", lambda e: errors.append(str(e)))
                    page.goto(url, wait_until="networkidle", timeout=60000)
                    page.wait_for_function("window.mockupReady === true", timeout=60000)
                    page.locator("#videoFile").set_input_files(str(media))
                    page.wait_for_function("document.querySelector('#screenVideo').readyState >= 2",
                                           timeout=30000)
                    if errors:
                        raise RuntimeError("Erro WebGL no navegador: " + "; ".join(errors))
                    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                           "-f", "image2pipe", "-framerate", str(fps),
                           "-vcodec", "png", "-i", "pipe:0", "-an", "-c:v", "libx264",
                           "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                           "-movflags", "+faststart", str(output)]
                    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=log)
                    try:
                        for i in range(frames):
                            page.evaluate("(t) => window.renderAt(t)", i / fps)
                            png = page.locator("#view").screenshot(type="png")
                            proc.stdin.write(png)
                    except Exception:
                        proc.kill()
                        raise
                    finally:
                        if proc.stdin and not proc.stdin.closed:
                            try:
                                proc.stdin.close()
                            except BrokenPipeError:
                                pass
                    if proc.wait(timeout=120) != 0:
                        raise RuntimeError("FFmpeg falhou: " + log_path.read_text(errors="replace")[-1000:])
                finally:
                    browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
    return {"output": str(output), "frames": frames, "fps": fps, "device": device,
            "motion": motion, "aspect": aspect, "width": width, "height": height,
            "backend": "threejs-local", "autopublish": False}


def main():
    parser = argparse.ArgumentParser(description="Renderizar vídeo real na tela de notebook/monitor 3D")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", choices=sorted(DEVICES), default="laptop")
    parser.add_argument("--motion", choices=sorted(MOTIONS), default="enter")
    parser.add_argument("--aspect", choices=sorted(ASPECTS), default="16:9")
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--frames", type=int, default=120)
    args = parser.parse_args()
    import json
    print(json.dumps(render_mockup(args.input, args.output, device=args.device,
                                   motion=args.motion, aspect=args.aspect,
                                   fps=args.fps, frames=args.frames),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
