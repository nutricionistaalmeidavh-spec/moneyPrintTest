"""Busca opcional de vídeos gratuitos no Wikimedia Commons, sem API key.

Use only CC0 or CC BY assets with machine-readable license metadata. Each
selected clip produces an attribution record for use in the final post.
"""
from __future__ import annotations

from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import time
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

API_URL = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = ("MoneyPrintTest/0.2 (https://github.com/nutricionistaalmeidavh-spec/"
              "moneyPrintTest; automated license-aware footage search)")
MAX_FILE_BYTES = 60 * 1024 * 1024
LIMIT = 3
ALLOWED_EXTENSIONS = (".webm", ".ogv", ".mpeg", ".mpg")


class CommonsError(RuntimeError):
    """External media lookup failed: use local fallback when requested."""


class _PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data: str):
        self.parts.append(data)


def plain_text(value: str) -> str:
    parser = _PlainText()
    parser.feed(str(value))
    return re.sub(r"\s+", " ", unescape(" ".join(parser.parts))).strip()[:300]


def approved_license(raw_url: str) -> tuple[str, str] | None:
    """Allow only licenses without share-alike restrictions."""
    parsed = urlsplit(str(raw_url).strip())
    if parsed.scheme != "https" or parsed.hostname != "creativecommons.org":
        return None
    path = parsed.path.rstrip("/")
    match = re.fullmatch(r"/licenses/by/(2\.0|2\.5|3\.0|4\.0)", path)
    if match:
        return "CC BY " + match.group(1), raw_url
    if path == "/publicdomain/zero/1.0":
        return "CC0 1.0", raw_url
    return None


def metadata_value(meta: dict, key: str) -> str:
    value = meta.get(key, {})
    return str(value.get("value", "")) if isinstance(value, dict) else ""


def parse_candidates(data: dict) -> list[dict]:
    pages = data.get("query", {}).get("pages", [])
    if isinstance(pages, dict):
        pages = list(pages.values())
    if not isinstance(pages, list):
        return []
    clips = []
    for page in pages:
        try:
            info = page["imageinfo"][0]
            url = info["url"]
            size = int(info["size"])
            meta = info["extmetadata"]
            license_info = approved_license(metadata_value(meta, "LicenseUrl"))
            download = urlsplit(url)
            title = page["title"]
            if (info.get("mediatype") != "VIDEO" or
                not license_info or
                download.scheme != "https" or
                download.hostname != "upload.wikimedia.org" or
                not download.path.startswith("/wikipedia/commons/") or
                not download.path.lower().endswith(ALLOWED_EXTENSIONS) or
                size < 4096 or size > MAX_FILE_BYTES or
                not title.startswith("File:")):
                continue
            author = plain_text(metadata_value(meta, "Artist"))
            if license_info[0] != "CC0 1.0" and not author:
                continue
            source = info.get("descriptionurl", "")
            if (urlsplit(source).hostname != "commons.wikimedia.org" or
                not source.startswith("https://")):
                continue
            clips.append({
                "title": title,
                "url": url,
                "source": source,
                "author": author or "Autor não informado",
                "license": license_info[0],
                "license_url": license_info[1],
                "size": size,
            })
        except (KeyError, TypeError, ValueError, IndexError):
            continue
    return clips


def api_search(term: str) -> list[dict]:
    query = urlencode({
        "action": "query", "generator": "search", "gsrsearch": f"{term} filetype:video",
        "gsrnamespace": 6, "gsrlimit": 16, "prop": "imageinfo",
        "iiprop": "url|size|mediatype|extmetadata",
        "format": "json", "formatversion": 2,
        "maxlag": 5,
    })
    request = Request(API_URL + "?" + query,
                      headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=35) as result:
        payload = json.load(result)
    if "error" in payload:
        raise CommonsError("Commons API recusou busca")
    return parse_candidates(payload)


def fetch_file(url: str, target: Path):
    """Download capped by size and hosted strictly on Wikimedia CDN."""
    if (urlsplit(url).scheme != "https" or
        urlsplit(url).hostname != "upload.wikimedia.org"):
        raise CommonsError("URL de mídia fora do Commons")
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".part")
    try:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=90) as response:
            if urlsplit(response.geturl()).hostname != "upload.wikimedia.org":
                raise CommonsError("Redirecionamento inseguro")
            total = 0
            with tmp.open("wb") as out:
                while block := response.read(1024 * 1024):
                    total += len(block)
                    if total > MAX_FILE_BYTES:
                        raise CommonsError("Vídeo excedeu limite de 60 MiB")
                    out.write(block)
        if total < 4096:
            raise CommonsError("Vídeo vazio")
        tmp.replace(target)
    finally:
        tmp.unlink(missing_ok=True)


def transcode_video(source: Path, target: Path, seconds: int = 12):
    """Convert WebM/OGV to H264 MP4 that MPT accepts as local media."""
    run = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
         "-i", str(source), "-t", str(seconds), "-an", "-vf",
         "scale='min(720,iw)':-2,fps=24",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "27",
         "-pix_fmt", "yuv420p", str(target)],
        check=False, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=180,
    )
    if run.returncode or not target.is_file() or target.stat().st_size < 4096:
        target.unlink(missing_ok=True)
        raise CommonsError("Conversão do vídeo Commons falhou")


def source_credits(records: list[dict]) -> str:
    lines = [
        "Créditos de vídeo – Wikimedia Commons",
        "As mídias foram cortadas e/ou convertidas para MP4.",
        "Ao publicar, inclua estes créditos e os links das licenças na descrição.",
        "",
    ]
    for record in records:
        lines.append(
            f"- {record['title']} | Autor: {record['author']} | "
            f"Origem: {record['source']} | "
            f"Licença: {record['license']} ({record['license_url']}) | "
            "Alterações: corte, redimensionamento e edição."
        )
    return "\n".join(lines) + "\n"


def find_free_videos(terms: list[str], dest: Path, max_results: int = LIMIT):
    """Return local MP4 paths and attribution records, or empty lists.

    API/network failures are soft: fallback to original local slides in auto mode.
    """
    records = []
    paths = []
    seen = set()
    folder = dest / "wikimedia"
    for term in terms[:6]:
        if len(paths) >= max_results:
            break
        try:
            candidates = api_search(term)
        except (OSError, ValueError, CommonsError, TimeoutError) as exc:
            print(f"Aviso: busca Commons indisponível para {term!r}: {type(exc).__name__}", flush=True)
            continue
        for item in candidates:
            if item["url"] in seen:
                continue
            seen.add(item["url"])
            original = folder / f"download-{len(seen)}{Path(urlsplit(item['url']).path).suffix}"
            target = folder / f"clip_{len(paths)+1}.mp4"
            try:
                fetch_file(item["url"], original)
                transcode_video(original, target)
            except (OSError, CommonsError, subprocess.TimeoutExpired, TimeoutError) as exc:
                print(f"Aviso: mídia Commons ignorada ({type(exc).__name__})", flush=True)
                target.unlink(missing_ok=True)
                continue
            finally:
                original.unlink(missing_ok=True)
            records.append(item)
            paths.append(str(target.resolve()))
            if len(paths) >= max_results:
                break
        time.sleep(0.5)
    if records:
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "creditos.txt").write_text(source_credits(records), encoding="utf-8")
        (dest / "licencas_midia.json").write_text(
            json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    return paths, records
