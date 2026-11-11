"""Read-only capture of ERPNext's publicly offered demonstration.

Authenticity policy:
- only the explicitly allowlisted official public demo host;
- no credentials, form submission, modifications, payments or account creation;
- never fake an interactive application from a login page or error;
- never stamp technical provenance labels on the exported video;
- preserve source URLs, capture states and failures in the diagnostic JSON only.
"""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse
import json

DEMO_HOST = "erpnext-demo.frappe.cloud"
DEMO_ENTRY = "https://erpnext-demo.frappe.cloud/api/method/erpnext_demo.erpnext_demo.auth.login_demo"
APP_ROUTES = {"home": "/app/home", "selling": "/app/selling", "stock": "/app/stock"}

def allowed_capture_target(url: str) -> bool:
    parts = urlparse(url)
    return (parts.scheme=="https" and parts.hostname==DEMO_HOST
            and parts.port in (None,443) and not parts.username and not parts.password
            and (parts.path.startswith("/app/") or parts.path.startswith("/api/method/erpnext_demo.erpnext_demo.auth/login_demo"))
            and not parts.query and not parts.fragment)

def is_readable_app(url: str, visible_text: str) -> bool:
    parts=urlparse(url)
    if not allowed_capture_target(url) or not parts.path.startswith("/app/"):
        return False
    text=visible_text.strip().lower()
    if len(text)<25:
        return False
    if "login to frappe" in text or "forgot password" in text:
        return False
    return True

def capture_demo_views(output: Path, *, width=1440, height=900) -> dict:
    """Try the official public demo; never fabricate a missing screen.

    A capture is accepted only after reaching an actual /app/ page with
    recognizable app content; failure is recorded and callers use real README
    screenshots instead. The site may change or reject anonymous access.
    """
    out=Path(output)
    out.mkdir(parents=True,exist_ok=True)
    provenance={"source":DEMO_ENTRY,"type":"real_browser_navigation",
                "allowed_host":DEMO_HOST,"screens":{},"errors":[]}
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as engine:
            browser=engine.chromium.launch(headless=True)
            context=browser.new_context(viewport={"width":width,"height":height},
                device_scale_factor=1,color_scheme="light",accept_downloads=False,
                service_workers="block",reduced_motion="reduce")
            try:
                page=context.new_page()
                # Restrict top-level navigation and script-initiated document
                # URLs; ordinary same-origin subresources remain available.
                def no_external_navigation(route):
                    request=route.request
                    if request.is_navigation_request() and request.frame == page.main_frame:
                        if allowed_capture_target(request.url):
                            route.continue_()
                        else:
                            route.abort()
                    else:
                        route.continue_()
                context.route("**/*",no_external_navigation)
                response=page.goto(DEMO_ENTRY,wait_until="domcontentloaded",timeout=35000)
                if not response or response.status>=400:
                    raise RuntimeError("Demo publicamente inacessível")
                for key,path in APP_ROUTES.items():
                    try:
                        target="https://"+DEMO_HOST+path
                        page.goto(target,wait_until="domcontentloaded",timeout=25000)
                        page.wait_for_timeout(1200)
                        body=page.locator("body").inner_text(timeout=6000)
                        if not is_readable_app(page.url,body):
                            raise ValueError("Página não comprovou interface acessível")
                        # A screenshot can still be of an error. Require actual
                        # Frappe Desk modules, nav, or recognized workspaces.
                        app_text=body.lower()
                        app_hints=("workspace","selling","sales","stock","inventory",
                                   "erpnext","modules","customer","purchase","accounting")
                        if not any(hint in app_text for hint in app_hints):
                            raise ValueError("Módulos não encontrados na interface")
                        dest=out/f"erpnext_{key}.png"
                        page.screenshot(path=str(dest),animations="disabled",
                            full_page=False,timeout=12000)
                        provenance["screens"][key]={"path":str(dest),"url":page.url,
                             "source":"public_demo","capture":"real_screenshot"}
                    except Exception as exc:
                        provenance["errors"].append(f"{key}: {type(exc).__name__}: {str(exc)[:160]}")
            finally:
                context.close()
                browser.close()
    except Exception as exc:
        provenance["errors"].append(f"demo: {type(exc).__name__}: {str(exc)[:160]}")
    provenance["has_real_navigation"]=len(provenance["screens"])>=2
    (out/"demo_capture_diagnostic.json").write_text(
        json.dumps(provenance,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return provenance
