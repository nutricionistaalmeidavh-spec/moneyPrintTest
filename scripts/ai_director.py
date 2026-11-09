"""MoneyPrint AI director: real sources in, verified shot IDs out.

Free local Ollama plans the edit. It is never trusted to invent links, news,
licenses, or filenames. All external assets are verified before the prompt.
"""
from __future__ import annotations

import base64
import email.utils
import ipaddress
import json
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    from .browser_capture import validate_repo_urls
except ImportError:
    from browser_capture import validate_repo_urls

AGENT_MODEL = "qwen2.5:1.5b"
NEWS_RSS = "https://news.google.com/rss/search?"
MAX_NEWS_DAYS = 90
MEDIA_HOSTS = {"raw.githubusercontent.com", "user-images.githubusercontent.com"}


def validate_sections(raw: object, urls: list[str]) -> list[dict]:
    if not isinstance(raw, list) or len(raw) != len(urls):
        raise ValueError("sections deve ter exatamente uma seção por repo_urls")
    result = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict) or set(item) - {
            "repo_url", "title", "narration", "broll_query"
        }:
            raise ValueError("Campos inválidos em sections")
        if item.get("repo_url") != urls[i]:
            raise ValueError("A ordem de sections precisa coincidir com repo_urls")
        title, narration, query = item.get("title"), item.get("narration"), item.get("broll_query", "")
        if not isinstance(title, str) or not 2 <= len(title.strip()) <= 75 or "\n" in title:
            raise ValueError("Título inválido em sections")
        if not isinstance(narration, str) or not 15 <= len(narration.strip()) <= 1700 or "\x00" in narration:
            raise ValueError("Narração de seção inválida (15 a 1700 caracteres)")
        if not isinstance(query, str) or len(query) > 70 or "\n" in query or "\r" in query:
            raise ValueError("broll_query inválida")
        result.append({"repo_url": urls[i], "title": title.strip(),
                       "narration": narration.strip(), "broll_query": query.strip()})
    return result


def _safe_web_url(url: object) -> bool:
    if not isinstance(url, str) or len(url) > 1200:
        return False
    try:
        parsed = urllib.parse.urlsplit(url)
        host = parsed.hostname
        if parsed.scheme != "https" or not host or parsed.username or parsed.password or parsed.port:
            return False
        if any(ord(c) < 32 for c in url) or host.endswith(".local") or "." not in host:
            return False
        try:
            ipaddress.ip_address(host)
            return False
        except ValueError:
            return True
    except ValueError:
        return False


def canonical_news_record(item: object) -> dict | None:
    if not isinstance(item, dict):
        return None
    title, publisher = item.get("headline"), item.get("publisher")
    date_text, url = item.get("published_at"), item.get("url")
    if not isinstance(title, str) or not 12 <= len(title.strip()) <= 185:
        return None
    if not isinstance(publisher, str) or not 2 <= len(publisher.strip()) <= 65:
        return None
    if not _safe_web_url(url) or not isinstance(date_text, str):
        return None
    try:
        dt = datetime.fromisoformat(date_text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return None
        if dt > datetime.now(timezone.utc) + timedelta(days=1):
            return None
        if datetime.now(timezone.utc) - dt > timedelta(days=MAX_NEWS_DAYS):
            return None
    except (ValueError, OverflowError):
        return None
    return {"headline": title.strip(), "publisher": publisher.strip(),
            "url": url, "published_at": dt.isoformat()}


def fetch_news_headline(repo: str) -> dict | None:
    """One verifiable RSS headline; failure means omit news, never invent one."""
    name = repo.rstrip("/").split("/")[-1]
    query = urllib.parse.urlencode({"q": f'"{name}" open source when:90d', "hl": "en",
                                    "gl": "US", "ceid": "US:en"})
    request = urllib.request.Request(NEWS_RSS + query,
                                     headers={"User-Agent": "MoneyPrintTest/0.3"})
    try:
        with urllib.request.urlopen(request, timeout=12) as reply:
            if urllib.parse.urlsplit(reply.geturl()).hostname != "news.google.com":
                return None
            data = reply.read(500_000)
        root = ET.fromstring(data)
        for item in root.findall(".//channel/item")[:7]:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            published = (item.findtext("pubDate") or "")
            source = item.find("source")
            publisher = (source.text or "").strip() if source is not None else ""
            if name.casefold() not in title.casefold():
                continue
            dt = email.utils.parsedate_to_datetime(published)
            candidate = canonical_news_record({
                "headline": title, "url": link, "publisher": publisher,
                "published_at": dt.isoformat()
            })
            if candidate:
                return candidate
    except (OSError, ValueError, ET.ParseError, TypeError) as exc:
        print("Aviso: notícias não verificadas; ignorando:", type(exc).__name__, flush=True)
    return None


def approved_github_media_url(url: str) -> bool:
    try:
        u = urllib.parse.urlsplit(url)
        return (u.scheme == "https" and u.hostname in MEDIA_HOSTS and
                not u.username and not u.password and not u.query and
                u.path.lower().endswith(".gif"))
    except (ValueError, TypeError):
        return False


def official_repo_gif(repo: str, output: Path) -> str | None:
    """Only README GIF on GitHub's own CDN. Limited fetch, no arbitrary redirects."""
    owner, name = repo.rstrip("/").split("/")[-2:]
    api = f"https://api.github.com/repos/{owner}/{name}/readme"
    try:
        with urllib.request.urlopen(urllib.request.Request(
                api, headers={"User-Agent": "MoneyPrintTest/0.3",
                              "Accept": "application/vnd.github+json"}), timeout=12) as reply:
            payload = json.load(reply)
        markdown = base64.b64decode(payload["content"]).decode("utf-8", "replace")
        candidates = re.findall(r'https://(?:raw\.githubusercontent\.com|user-images\.githubusercontent\.com)/[^\s"()]+?\.gif', markdown, re.I)
        for url in candidates[:2]:
            if not approved_github_media_url(url):
                continue
            output.mkdir(parents=True, exist_ok=True)
            gif = output / "demo.gif"
            req = urllib.request.Request(url, headers={"User-Agent": "MoneyPrintTest/0.3"})
            with urllib.request.urlopen(req, timeout=20) as res:
                if not approved_github_media_url(res.geturl()):
                    continue
                length = 0
                with gif.open("wb") as out:
                    while block := res.read(1024 * 128):
                        length += len(block)
                        if length > 12 * 1024 * 1024:
                            raise ValueError("GIF grande demais")
                        out.write(block)
            target = output / "demo.mp4"
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                "-stream_loop", "-1", "-i", str(gif), "-t", "8", "-an",
                "-vf", "fps=24,scale=1280:720:force_original_aspect_ratio=decrease,"
                       "pad=1280:720:(ow-iw)/2:(oh-ih)/2",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "25",
                "-pix_fmt", "yuv420p", str(target),
            ], check=True, timeout=90)
            gif.unlink(missing_ok=True)
            if target.stat().st_size > 4096:
                return str(target.resolve())
    except (OSError, KeyError, TypeError, ValueError, subprocess.SubprocessError):
        pass
    return None


def validate_director_plan(value: object, asset_ids: set[str]) -> list[dict] | None:
    if not isinstance(value, dict) or not isinstance(value.get("shots"), list):
        return None
    shots = value["shots"]
    if not shots:
        return None
    clean = []
    for shot in shots:
        if not isinstance(shot, dict) or set(shot) != {"asset_id", "seconds"}:
            return None
        if shot["asset_id"] not in asset_ids or type(shot["seconds"]) is not int:
            return None
        if shot["seconds"] <= 0:
            return None
        clean.append({"asset_id": shot["asset_id"], "seconds": shot["seconds"]})
    return clean


def build_fallback_plan(ids: list[str], preferred: list[str]) -> list[dict]:
    if not ids:
        raise ValueError("Sem vídeo de repositório aprovado")
    github_id = ids[0]
    chosen = [github_id]
    extras = [key for key in preferred if key in ids and key != github_id]
    for extra in extras:
        chosen.extend([extra, github_id])
    if len(chosen) == 1:
        return [{"asset_id": github_id, "seconds": 12}]
    return [{"asset_id": key, "seconds": 5 if key != github_id else 7} for key in chosen]


def plan_with_local_ai(section: dict, assets: list[dict]) -> tuple[list[dict], str]:
    ids = {entry["id"] for entry in assets}
    fallback = build_fallback_plan(
        [assets[0]["id"]] + [a["id"] for a in assets[1:]],
        [a["id"] for a in assets[1:]])
    prompt = (
        "Você é editor de um documentário tecnológico em português. "
        "Planeje takes elegantes de duração livre, equilibrando cenas rápidas e cenas de demonstração. "
        "Use APENAS asset_id da lista verificada; priorize gravação GitHub real, "
        "intercale b-roll contextual, GIF oficial e manchete verificada SE EXISTIREM. "
        "Nunca invente assets, manchetes nem fontes. Use navegação em vários takes. "
        "Devolva SOMENTE JSON com {\"shots\":[{\"asset_id\":\"...\",\"seconds\":5}]}. "
        "Repositório: " + section["title"] + ". Narração: " + section["narration"][:800] +
        ". Assets verificados: " + json.dumps(
            [{"id": a["id"], "kind": a["kind"]} for a in assets], ensure_ascii=False)
    )
    try:
        request = urllib.request.Request("http://127.0.0.1:11434/api/generate",
              data=json.dumps({"model": AGENT_MODEL, "prompt": prompt,
                               "stream": False, "format": "json",
                               "options": {"temperature": 0.15, "num_predict": 350}}).encode(),
              headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=150) as reply:
            raw = json.load(reply)
        parsed = json.loads(raw["response"])
        verified = validate_director_plan(parsed, ids)
        if verified:
            if assets[0]["id"] not in [s["asset_id"] for s in verified]:
                return fallback, "fallback:missing_repo"
            return verified, "ollama:verified"
    except (OSError, ValueError, TypeError, KeyError):
        pass
    return fallback, "fallback:invalid_ai_output"


def suggest_broll_query(section: dict) -> tuple[str, str]:
    """Have the local director plan a practical real-world stock-footage search."""
    default = section.get("broll_query", "").strip()
    prompt = (
        "Você é pesquisador visual. Escolha UMA busca concreta em inglês para "
        "vídeo real do Wikimedia Commons relacionado ao USO da ferramenta, "
        "por exemplo 'restaurant cashier serving customer' para PDV. "
        "Não peça vídeo de interface de site. "
        "JSON somente: {\"query\": \"...\"}. "
        "Repositório: " + section["title"] + "; contexto: " +
        section["narration"][:500]
    )
    try:
        data = json.dumps({"model": AGENT_MODEL, "prompt": prompt,
                           "stream": False, "format": "json",
                           "options": {"temperature": 0.18, "num_predict": 100}}).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate", data=data,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=90) as response:
            raw = json.load(response)
        query = json.loads(raw["response"]).get("query")
        if isinstance(query, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ,'-]{3,65}", query):
            return query, "ollama"
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return default or "computer software developer", "fallback"


def official_repo_image(repo: str, output: Path) -> str | None:
    """Download a real project screenshot linked in its GitHub README."""
    owner, name = repo.rstrip("/").split("/")[-2:]
    api = f"https://api.github.com/repos/{owner}/{name}/readme"
    try:
        with urllib.request.urlopen(urllib.request.Request(
                api, headers={"User-Agent": "MoneyPrintTest/0.3",
                              "Accept": "application/vnd.github+json"}), timeout=14) as reply:
            payload = json.load(reply)
        markdown = base64.b64decode(payload["content"]).decode("utf-8", "replace")
        pattern = r'https://(?:raw\.githubusercontent\.com|user-images\.githubusercontent\.com)/[^\s"()]+?\.(?:png|jpg|jpeg|webp)'
        urls = re.findall(pattern, markdown, re.I)
        for url in urls[:4]:
            if (not _safe_web_url(url) or
                urllib.parse.urlsplit(url).hostname not in MEDIA_HOSTS):
                continue
            target = output / "project_screenshot.png"
            output.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(urllib.request.Request(
                    url, headers={"User-Agent": "MoneyPrintTest/0.3"}), timeout=22) as reply:
                if urllib.parse.urlsplit(reply.geturl()).hostname not in MEDIA_HOSTS:
                    continue
                data = reply.read(8_000_001)
            if len(data) > 8_000_000:
                continue
            # Pillow verifies image bytes and converts disparate formats to PNG.
            from PIL import Image, UnidentifiedImageError
            from io import BytesIO
            with Image.open(BytesIO(data)) as image:
                if image.width < 240 or image.height < 140:
                    continue
                image.convert("RGB").save(target)
            return str(target.resolve())
    except (OSError, KeyError, TypeError, ValueError, UnboundLocalError):
        pass
    return None
