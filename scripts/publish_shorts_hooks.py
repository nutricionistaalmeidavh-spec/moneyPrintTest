"""Prepara um release interno de 110 MP4s de ganchos a partir de artefatos validados.

NÃO cria vídeos: apenas copia os bytes originais, confere SHA256 e produz catálogo.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

SLUGS = (
    ("motorcycle-crash", "crash"), ("bike-crash-in-hole", "crash"),
    ("extreme-bike-crash", "crash"), ("head-on-crash", "crash"),
    ("pool-jump-fail", "water"), ("wall-climber", "sports"),
    ("face-plant", "funny"), ("skate-slip", "sports"),
    ("truck-flip", "crash"), ("bad-drop-in", "sports"),
)
SAFE_FILENAME = re.compile(r"^[0-9]{3}_[A-Za-z0-9_.-]+\.mp4$")

def file_info(path):
    report = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=width,height,codec_type",
        "-of", "json", str(path)], text=True)
    content = json.loads(report)
    stream = next(s for s in content["streams"] if s.get("codec_type") == "video")
    return {"duracao_segundos": round(float(content["format"]["duration"]), 4),
            "width": stream["width"], "height": stream["height"]}

def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as fd:
        for chunk in iter(lambda: fd.read(1024*1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def build(batch100, batch10, destination):
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Pasta de destino deve estar vazia para nao misturar releases")
    destination.mkdir(parents=True, exist_ok=True)
    catalog_path = batch100 / "CATALOGO.csv"
    rows = list(csv.DictReader(catalog_path.open("r", encoding="utf-8-sig", newline="")))
    if len(rows) != 100:
        raise ValueError(f"Lote de 100 incompleto: {len(rows)}")
    catalog, seen = [], set()
    for source_row in rows:
        filename = source_row["arquivo"]
        if not SAFE_FILENAME.fullmatch(filename):
            raise ValueError("Caminho de arquivo inseguro: "+filename)
        source = batch100 / filename
        if not source.is_file():
            raise ValueError("MP4 ausente: "+filename)
        check = sha(source)
        if check != source_row["sha256"]:
            raise ValueError("SHA256 nao confere: "+filename)
        metadata = file_info(source)
        if check in seen or not .4 <= metadata["duracao_segundos"] <= 30:
            raise ValueError("MP4 duplicado ou fora de duracao: "+filename)
        seen.add(check)
        shutil.copyfile(source, destination/filename)
        catalog.append({
          "arquivo": filename, "categoria": source_row["categoria"],
          "sha256": check, "duracao_segundos": metadata["duracao_segundos"],
          "origem": source_row["origem"]
        })
    for index,(slug,category) in enumerate(SLUGS,101):
        filename = f"{index:03d}_{slug}.mp4"
        source = batch10 / f"{slug}.mp4"
        if not source.is_file():
            raise ValueError("MP4 do primeiro lote ausente: "+slug)
        check = sha(source)
        metadata = file_info(source)
        if check in seen:
            raise ValueError("Video repetido: "+slug)
        seen.add(check)
        shutil.copyfile(source,destination/filename)
        catalog.append({
          "arquivo":filename,"categoria":category,"sha256":check,
          "duracao_segundos":metadata["duracao_segundos"],
          "origem":"https://viralhookup.com/hook/"+slug
        })
    from scripts.shorts_hooks import validate_catalog
    validate_catalog(catalog)
    if len(catalog)!=110:
        raise ValueError("Esperados 110 MP4s")
    (destination/"CATALOGO.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    (destination/"ORIGEM_E_DIREITOS.txt").write_text(
        "MoneyPrint — 110 ganchos originais do ViralHook.\n"
        "Arquivos armazenados para integracao tecnica interna do workflow Shorts.\n"
        "Origem de cada arquivo no CATALOGO.json.\n"
        "ATENCAO: direito de republicacao/comercializacao ainda nao foi verificado.\n"
        "Nao redistribua publicamente ou monetize sem confirmar licencas.\n",
        encoding="utf-8"
    )
    print("110/110 MP4s validados; catalogo JSON gerado; nenhum video renderizado.")
    return catalog

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--batch-100",required=True,type=Path)
    parser.add_argument("--batch-10",required=True,type=Path)
    parser.add_argument("--out",required=True,type=Path)
    a=parser.parse_args()
    build(a.batch_100,a.batch_10,a.out)

if __name__=="__main__":
    main()
