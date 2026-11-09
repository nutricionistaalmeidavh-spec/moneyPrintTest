#!/usr/bin/env python3
"""Download 100 additional, unique, unedited viral-hook MP4 files."""
from __future__ import annotations
import argparse, csv, hashlib, json, re, subprocess, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://viralhookup.com"
EXCLUDED = frozenset("motorcycle-crash bike-crash-in-hole extreme-bike-crash head-on-crash pool-jump-fail wall-climber face-plant skate-slip truck-flip bad-drop-in".split())
QUOTAS = [("crash", 45), ("funny", 35), ("sports", 15), ("water", 5)]
PATTERN = re.compile(r'href=["\'](?:https?://viralhookup\.com)?/hook/([a-z0-9][a-z0-9-]*)["\']', re.I)
MAX_BYTES = 35 * 1024 * 1024

def download(url):
    error = None
    for i in range(3):
        try:
            headers = {"User-Agent": "Mozilla/5.0", "Accept": "text/html,video/mp4,*/*"}
            with urlopen(Request(url, headers=headers), timeout=40) as r:
                return r.read(MAX_BYTES + 1) if "/api/download/" in url else r.read()
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            error = exc
            if i < 2:
                time.sleep(i + 1)
    raise RuntimeError(f"{url}: {error}")

def parse_slugs(html):
    return list(dict.fromkeys(PATTERN.findall(html)))

def catalog(category):
    seen = []
    for page in range(1, 18):
        url = BASE + "/?" + urlencode({"niche": category, "page": page, "sort": "popular"})
        slugs = parse_slugs(download(url).decode("utf-8", "replace"))
        fresh = [name for name in slugs if name not in seen]
        seen.extend(fresh)
        print(f"catalog {category}: page={page} found={len(seen)} new={len(fresh)}", flush=True)
        if not fresh or len(slugs) < page * 24:
            break
    return seen

def candidates_for(catalogs, excluded=EXCLUDED):
    selected = []
    used = set(excluded)
    for category, quota in QUOTAS:
        count = 0
        for slug in catalogs.get(category, []):
            if slug not in used:
                selected.append((slug, category))
                used.add(slug)
                count += 1
                if count >= quota + 20:
                    break
    for category, slugs in catalogs.items():
        for slug in slugs:
            if slug not in used:
                selected.append((slug, category))
                used.add(slug)
    return selected

def analyze_file(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_name,codec_type,width,height:format=duration",
                        "-of", "json", str(path)],
                       check=True, capture_output=True, text=True, timeout=15)
    info = json.loads(r.stdout)
    video = next(s for s in info["streams"] if s.get("codec_type") == "video")
    return {"duration": round(float(info["format"]["duration"]), 3),
            "width": video["width"], "height": video["height"],
            "codec": video["codec_name"]}

def get_clip(slug, category, staging):
    data = download(BASE + "/api/download/" + slug)
    if len(data) > MAX_BYTES or len(data) < 2500 or b"ftyp" not in data[4:16]:
        raise ValueError("Invalid or oversized MP4")
    path = staging / (slug + ".mp4")
    path.write_bytes(data)
    try:
        metadata = analyze_file(path)
        if not 0.45 <= metadata["duration"] <= 15.5:
            raise ValueError(f"Incompatible duration {metadata['duration']}s")
        return {"slug": slug, "category": category, "path": path,
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data), **metadata}
    except Exception:
        path.unlink(missing_ok=True)
        raise

def collect(target, folder):
    folder.mkdir(parents=True, exist_ok=True)
    staging = folder / "_downloads"
    staging.mkdir(exist_ok=True)
    catalogs = {c: catalog(c) for c, _ in QUOTAS}
    candidates = candidates_for(catalogs)
    print(f"Unique candidates: {len(candidates)}", flush=True)
    accepted, hashes, errors = [], set(), []
    with ThreadPoolExecutor(max_workers=6) as pool:
        for pos in range(0, len(candidates), 12):
            if len(accepted) >= target:
                break
            futures = {pool.submit(get_clip, slug, cat, staging): slug
                       for slug, cat in candidates[pos:pos + 12]}
            for future in as_completed(futures):
                slug = futures[future]
                try:
                    clip = future.result()
                    if clip["sha256"] in hashes or len(accepted) >= target:
                        clip["path"].unlink(missing_ok=True)
                        if clip["sha256"] in hashes:
                            errors.append({"slug": slug, "reason": "duplicate SHA256"})
                    else:
                        hashes.add(clip["sha256"])
                        accepted.append(clip)
                except Exception as exc:
                    errors.append({"slug": slug, "reason": str(exc)[:200]})
            print(f"Downloaded {len(accepted)}/{target}; rejected={len(errors)}", flush=True)
    rows = []
    for number, clip in enumerate(accepted[:target], 1):
        filename = f"{number:03d}_{clip['category']}_{clip['slug']}.mp4"
        clip["path"].rename(folder / filename)
        rows.append({"numero": number, "arquivo": filename,
                     "categoria": clip["category"],
                     "duracao_segundos": clip["duration"],
                     "largura": clip["width"], "altura": clip["height"],
                     "codec": clip["codec"], "tamanho_bytes": clip["bytes"],
                     "sha256": clip["sha256"],
                     "origem": BASE + "/hook/" + clip["slug"]})
    for temp in staging.iterdir():
        temp.unlink()
    staging.rmdir()
    with (folder / "CATALOGO.csv").open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]) if rows else ["arquivo"])
        writer.writeheader()
        writer.writerows(rows)
    (folder / "RELATORIO.json").write_text(json.dumps(
        {"requested": target, "downloaded": len(rows),
         "excluded_from_prior_batch": sorted(EXCLUDED),
         "rejected": errors, "catalog": rows}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    (folder / "LEIA-ME.txt").write_text(
        "100 ganchos adicionais do ViralHook, MP4s originais sem edicao,"
        " render, corte ou legenda. O CSV apresenta origem e metadados.\n"
        "Download gratuito nao comprova direito de reutilizacao"
        " ou uso comercial: confirmar licenca de cada clipe antes de publicar.\n",
        encoding="utf-8")
    print(f"FINAL: {len(rows)}/{target} MP4s validos adicionais", flush=True)
    if len(rows) != target:
        raise SystemExit("Partial results; inspect artifact and report")

if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("--target", type=int, default=100)
    cli.add_argument("--output", default="100_CORTES_VIRAIS")
    args = cli.parse_args()
    collect(args.target, Path(args.output))
