"""Fotos gratuitas para carrosséis: Pixabay (opt-in via secret) e Commons."""
from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import time
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from scripts.commons_media import approved_license

API_COMMONS = "https://commons.wikimedia.org/w/api.php"
API_PIXABAY = "https://pixabay.com/api/"
USER_AGENT = "MoneyPrintTest/0.3 (https://github.com/nutricionistaalmeidavh-spec/moneyPrintTest)"
MAX_PHOTO_BYTES = 24 * 1024 * 1024
CACHE_TTL = 24 * 60 * 60


class PhotoError(RuntimeError):
    pass


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def html_plain(raw):
    parser = _TextExtractor()
    parser.feed(str(raw))
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()[:200]


def is_url(raw, hosts):
    try:
        parsed = urlsplit(str(raw))
        return (parsed.scheme == "https" and parsed.hostname in hosts
                and not parsed.username and not parsed.password and not parsed.port)
    except ValueError:
        return False


def safe_photo_url(url):
    return is_url(url, {"upload.wikimedia.org", "cdn.pixabay.com", "pixabay.com"})


def parse_candidates(data):
    """Validate full metadata for Commons photos; reject restricted licenses."""
    pages = data.get("query", {}).get("pages", [])
    if isinstance(pages, dict):
        pages = list(pages.values())
    result = []
    for page in pages if isinstance(pages, list) else []:
        try:
            info = page["imageinfo"][0]
            meta = info["extmetadata"]
            licensed = approved_license(meta.get("LicenseUrl", {}).get("value", ""))
            author = html_plain(meta.get("Artist", {}).get("value", ""))
            title = page["title"]
            src = info["url"]
            photo = info.get("thumburl") or src
            page_url = info["descriptionurl"]
            width, height = int(info["width"]), int(info["height"])
            size = int(info["size"])
            if (not licensed or not title.startswith("File:") or
                info["mediatype"] != "BITMAP" or not author and licensed[0] != "CC0 1.0" or
                not safe_photo_url(src) or urlsplit(src).hostname != "upload.wikimedia.org" or
                not safe_photo_url(photo) or urlsplit(photo).hostname != "upload.wikimedia.org" or
                not is_url(page_url, {"commons.wikimedia.org"}) or
                size <= 20000 or size > 55 * 1024 * 1024 or width < 900 or height < 600):
                continue
            result.append({
                "provider": "Wikimedia Commons", "title": title,
                "url": src, "download_url": photo, "source": page_url,
                "author": author or "Autor não informado", "license": licensed[0],
                "license_url": licensed[1], "width": width, "height": height,
            })
        except (KeyError, ValueError, IndexError, TypeError, AttributeError):
            continue
    return result


def parse_pixabay_candidates(data):
    """Pixabay's custom Content License permits edited works, not standalone resale."""
    out = []
    for hit in data.get("hits", []) if isinstance(data.get("hits", []), list) else []:
        try:
            if hit.get("type") != "photo":
                continue
            url = hit.get("fullHDURL") or hit.get("largeImageURL")
            source = hit.get("pageURL")
            width, height = int(hit["imageWidth"]), int(hit["imageHeight"])
            if (not safe_photo_url(url) or not is_url(source, {"pixabay.com"}) or
                width < 900 or height < 600 or not hit.get("user")):
                continue
            out.append({
                "provider": "Pixabay", "title": str(hit.get("tags", ""))[:140],
                "url": url, "download_url": url, "source": source,
                "author": str(hit["user"])[:100],
                "license": "Pixabay Content License",
                "license_url": "https://pixabay.com/service/terms/",
                "width": width, "height": height,
            })
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    return out


def photo_score(item):
    """Prefer calm desk/workspace images over gaming, neon and generated art."""
    title = " " + str(item.get("title", "")).lower() + " "
    positives = {
        "monitor": 230, "computer screen": 110, "multiple screens": 150,
        "dual monitor": 180, "desk setup": 160, "workstation": 150,
        "window": 135, "natural light": 135, "sunlight": 130,
        "plant": 105, "modern": 35, "minimal": 80,
        "keyboard": 70, "desk": 90, "workspace": 60, "office": 60,
        "computer": 35, "interior": 45, "room": 25,
    }
    negatives = {
        "notebook": -170, "pen": -135, "paper": -145,
        "notepad": -115, "book": -75, "writing": -60,
        "close up": -200, "closeup": -200, "macro": -195,
        "gamer": -250, "gaming": -245, "video game": -200,
        "playstation": -250, "console": -195, "anime": -200,
        "neon": -200, "3d": -230, "render": -200, "bedroom": -90,
    }
    quality = sum(weight for word, weight in positives.items() if word in title)
    quality += sum(weight for word, weight in negatives.items() if word in title)
    ratio = item["width"] / max(1, item["height"])
    portrait = 160 if ratio < 1.15 else 0
    resolution = (min(item["width"], 2000) + min(item["height"], 2200)) / 35
    return quality + portrait + resolution


def choose_candidate(items):
    if not items:
        raise PhotoError("Nenhuma foto licenciada foi encontrada")
    return max(items, key=photo_score)


def _get_json_cached(url, *, cache_dir):
    """Cache API responses for 24h; API secrets never enter cache filenames."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / (hashlib.sha256(url.encode()).hexdigest() + ".json")
    if target.is_file() and time.time() - target.stat().st_mtime < CACHE_TTL:
        try:
            return json.loads(target.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(req, timeout=35) as res:
        if not is_url(res.geturl(), {"pixabay.com", "commons.wikimedia.org"}):
            raise PhotoError("Redirecionamento inseguro na API")
        data = json.load(res)
    target.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def search_pixabay(term, key, cache_dir):
    if not key:
        return []
    query = urlencode({
        "key": key, "q": term[:100], "image_type": "photo", "safesearch": "true",
        "order": "popular", "per_page": 30, "min_width": 900,
    })
    return parse_pixabay_candidates(_get_json_cached(
        API_PIXABAY + "?" + query, cache_dir=cache_dir))


def search_commons(term, cache_dir):
    query = urlencode({
        "action": "query", "generator": "search",
        "gsrsearch": term[:90] + " filetype:bitmap",
        "gsrnamespace": 6, "gsrlimit": 24, "prop": "imageinfo",
        "iiprop": "url|size|mime|mediatype|extmetadata|dimensions",
        "iiurlwidth": 1600, "format": "json", "formatversion": 2,
    })
    return parse_candidates(_get_json_cached(
        API_COMMONS + "?" + query, cache_dir=cache_dir))


def search_free_photos(terms, source, env, cache_dir):
    """Pixabay preferred only when free API key explicitly configured."""
    key = env.get("PIXABAY_API_KEY", "").strip()
    if source == "pixabay" and not key:
        raise PhotoError("PIXABAY_API_KEY não configurada nos Secrets do GitHub")
    providers = (["pixabay", "wikimedia"] if source == "auto" and key else
                 ["wikimedia"] if source == "auto" else [source])
    all_items = []
    errors = []
    for provider in providers:
        for term in terms[:4]:
            try:
                items = (search_pixabay(term, key, cache_dir) if provider == "pixabay"
                         else search_commons(term, cache_dir))
                for item in items:
                    if not any(old["source"] == item["source"] for old in all_items):
                        all_items.append(item)
            except (OSError, PhotoError, ValueError, TimeoutError) as exc:
                errors.append(type(exc).__name__)
            # Evaluate all search terms: first-result popularity often selects
            # isolated laptops rather than the full desk setups requested.
            if len(all_items) >= 100:
                break
        if all_items:
            break
    if not all_items:
        raise PhotoError("Nenhuma foto livre disponível; revise a busca ou a conexão do provedor. "
                         + ", ".join(errors[:3]))
    return sorted(all_items, key=photo_score, reverse=True)


def download_photo(item, target):
    """Bounded size and allowed hostnames even after redirect."""
    url = item["download_url"]
    if not safe_photo_url(url):
        raise PhotoError("Origem de imagem não permitida")
    target.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "image/*"})
    tmp = target.with_suffix(".part")
    try:
        with urlopen(request, timeout=80) as res:
            if not safe_photo_url(res.geturl()):
                raise PhotoError("Redirecionamento de download não permitido")
            size = 0
            with tmp.open("wb") as out:
                while chunk := res.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_PHOTO_BYTES:
                        raise PhotoError("Imagem excede 24 MiB")
                    out.write(chunk)
        if size < 10_000:
            raise PhotoError("Imagem incompleta")
        from PIL import Image
        with Image.open(tmp) as im:
            im.verify()
        tmp.replace(target)
    finally:
        tmp.unlink(missing_ok=True)
