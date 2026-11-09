"""Capture crisp GitHub *stills* with Playwright for animated motion slides.

No video-scroll recording: scroll directly to meaningful README positions and
let FFmpeg animate the resulting screenshots deterministically.
"""
from __future__ import annotations
from pathlib import Path
from urllib.parse import urlsplit
import json

from scripts.browser_capture import validate_repo_urls, is_github_asset, CaptureError


def capture_repo_stills(urls: list[str], output: Path, *, width=1440, height=900) -> list[list[str]]:
    urls = validate_repo_urls(urls)
    if width < 640 or height < 480:
        raise ValueError("Viewport muito pequeno")
    from playwright.sync_api import sync_playwright
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    records = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for index, url in enumerate(urls, 1):
                context = browser.new_context(viewport={"width":width, "height":height},
                                              device_scale_factor=1,
                                              color_scheme="dark",
                                              reduced_motion="reduce",
                                              service_workers="block",
                                              accept_downloads=False)
                files = []
                try:
                    def allow(route):
                        if is_github_asset(urlsplit(route.request.url).hostname):
                            route.continue_()
                        else:
                            route.abort()
                    context.route("**/*", allow)
                    page = context.new_page()
                    res = page.goto(url, wait_until="domcontentloaded", timeout=45000)
                    if not res or res.status >= 400 or urlsplit(page.url).hostname != "github.com":
                        raise CaptureError("Não foi possível acessar repositório público: " + url)
                    page.wait_for_timeout(700)
                    folder = output / f"repo_{index:02d}"
                    folder.mkdir(parents=True, exist_ok=True)
                    top = folder / "top.png"
                    page.screenshot(path=str(top), animations="disabled")
                    files.append(str(top.resolve()))
                    # Jump, never mouse-wheel record. This avoids laggy 1-second
                    # steps, browser-load white flashes and wrong framing.
                    readme = page.locator("article.markdown-body, #readme").first
                    if readme.count():
                        for n, ratio in enumerate((0.0, 0.44), 1):
                            page.evaluate("""(ratio) => {
                              const el = document.querySelector('article.markdown-body, #readme');
                              if (!el) return;
                              const rect = el.getBoundingClientRect();
                              const top = rect.top + window.scrollY;
                              const y = top + Math.min(Math.max(0,el.scrollHeight-innerHeight), 
                                                       Math.max(0,el.scrollHeight-innerHeight)*ratio);
                              window.scrollTo({top: Math.max(0,y-88), behavior:'instant'});
                            }""", ratio)
                            page.wait_for_timeout(400)
                            dest = folder / f"readme_{n}.png"
                            page.screenshot(path=str(dest), animations="disabled")
                            files.append(str(dest.resolve()))
                    records.append(files)
                finally:
                    context.close()
        finally:
            browser.close()
    (output / "capturas.json").write_text(
        json.dumps([{"url":u,"screenshots":p} for u,p in zip(urls,records)],
                   ensure_ascii=False,indent=2),encoding="utf-8")
    return records
