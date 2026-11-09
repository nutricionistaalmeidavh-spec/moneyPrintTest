"""Record public GitHub repository pages as real desktop browser videos.

No device, private account, credentials or paid API is required.
"""
from __future__ import annotations

import math
import re
import subprocess
from pathlib import Path
from urllib.parse import urlsplit


class CaptureError(ValueError):
    """Unsafe or invalid video capture request."""


OWNER = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})\Z")
REPO = re.compile(r"[A-Za-z0-9_.-]{1,100}\Z")
ALLOWED_HOSTS = ("github.com", "githubassets.com", "githubusercontent.com")


def is_github_asset(host: str | None) -> bool:
    if not isinstance(host, str):
        return False
    host = host.lower()
    return any(host == suffix or host.endswith("." + suffix) for suffix in ALLOWED_HOSTS)


def validate_repo_urls(raw: object) -> list[str]:
    if not isinstance(raw, list) or not 1 <= len(raw) <= 12:
        raise CaptureError("repo_urls deve ter de 1 a 12 repositórios GitHub")
    result = []
    seen = set()
    for entry in raw:
        if (not isinstance(entry, str) or entry != entry.strip()
                or any(ord(c) < 32 for c in entry)):
            raise CaptureError("URL do repositório inválida")
        try:
            parsed = urlsplit(entry)
        except ValueError as exc:
            raise CaptureError("URL do repositório inválida") from exc
        path = parsed.path.removesuffix("/")
        parts = path.split("/")
        if (parsed.scheme != "https" or parsed.netloc != "github.com"
                or parsed.query or parsed.fragment or len(parts) != 3
                or parts[0] != "" or not OWNER.fullmatch(parts[1])
                or not REPO.fullmatch(parts[2]) or parts[2] in {".", ".."}):
            raise CaptureError("Apenas URLs https://github.com/owner/repo são aceitas")
        canonical = f"https://github.com/{parts[1]}/{parts[2]}"
        normalized = canonical.lower()
        if normalized in seen:
            raise CaptureError("Não repita o mesmo repositório")
        seen.add(normalized)
        result.append(canonical)
    return result


def capture_plan(urls: list[str], duration_seconds: int) -> list[tuple[str, int]]:
    safe_urls = validate_repo_urls(urls)
    if type(duration_seconds) is not int or not 15 <= duration_seconds <= 360:
        raise CaptureError("Duração permitida: 15 a 360 segundos")
    seconds = min(60, max(8, math.ceil(duration_seconds / len(safe_urls))))
    return [(url, seconds) for url in safe_urls]


def capture_repositories(urls: list[str], duration_seconds: int, output: Path, *, focus_readme: bool = False) -> list[str]:
    """Record real GitHub browser visits, converting WebM to MP4 via FFmpeg."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright e Chromium precisam estar instalados") from exc

    plan = capture_plan(urls, duration_seconds)
    output.mkdir(parents=True, exist_ok=True)
    raw_dir = output / "webm"
    raw_dir.mkdir(exist_ok=True)
    clips: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for index, (url, seconds) in enumerate(plan, 1):
                context = browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    record_video_dir=str(raw_dir),
                    record_video_size={"width": 1280, "height": 720},
                    device_scale_factor=1,
                    accept_downloads=False,
                    service_workers="block",
                )
                page = None
                webm = output / f"repository_{index:02d}.webm"
                try:
                    def guard(route):
                        host = urlsplit(route.request.url).hostname
                        if is_github_asset(host):
                            route.continue_()
                        else:
                            route.abort()

                    context.route("**/*", guard)
                    page = context.new_page()
                    response = page.goto(url, wait_until="domcontentloaded", timeout=45000)
                    if (not response or response.status >= 400
                            or urlsplit(page.url).hostname != "github.com"):
                        raise CaptureError(f"Página GitHub indisponível: {url}")
                    page.wait_for_timeout(1600)
                    remaining = max(0, seconds * 1000 - 1600)
                    if focus_readme and remaining >= 2800:
                        # Show name, description and stars first, then move the
                        # camera to actual README features instead of spending
                        # the whole take scrolling hundreds of code files.
                        page.wait_for_timeout(900)
                        remaining -= 900
                        try:
                            page.evaluate("""() => {
                              const readme = document.querySelector(
                                'article.markdown-body, #readme');
                              if (readme) {
                                const y = window.scrollY +
                                  readme.getBoundingClientRect().top - 80;
                                window.scrollTo({top:Math.max(0,y),behavior:'smooth'});
                              }
                            }""")
                            page.wait_for_timeout(1100)
                            remaining -= 1100
                        except Exception:
                            pass
                    while remaining > 0:
                        page.mouse.wheel(0, 340 if focus_readme else 360)
                        delay = min(1250, remaining)
                        page.wait_for_timeout(delay)
                        remaining -= delay
                        bottom = page.evaluate(
                            "window.scrollY + innerHeight >= document.documentElement.scrollHeight - 15")
                        if bottom:
                            if focus_readme:
                                page.evaluate("""() => {
                                  const el=document.querySelector(
                                    'article.markdown-body, #readme');
                                  window.scrollTo({
                                    top: el ? window.scrollY +
                                      el.getBoundingClientRect().top - 80 : 0,
                                    behavior:'instant'
                                  });
                                }""")
                            else:
                                page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
                    page.close()
                    context.close()  # Flushes the recorded WebM.
                    page.video.save_as(webm)
                finally:
                    if page and not page.is_closed():
                        page.close()
                    context.close()

                mp4 = output / f"repository_{index:02d}.mp4"
                subprocess.run([
                    "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                    "-i", str(webm), "-an", "-r", "24", "-vf", "scale=1280:720:flags=lanczos",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "26",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(mp4),
                ], check=True, timeout=240)
                if not mp4.exists() or mp4.stat().st_size < 4096:
                    raise CaptureError(f"Captura de vídeo vazia: {url}")
                webm.unlink(missing_ok=True)
                clips.append(str(mp4.resolve()))
        finally:
            browser.close()
    return clips
