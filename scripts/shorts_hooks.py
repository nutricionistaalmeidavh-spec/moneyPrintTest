"""Seleciona um gancho local dos assets persistentes do release do repositório.

Não renderiza, não altera nem publica vídeos; exige arquivo MP4 com SHA256
registrado no catálogo, que o workflow verifica após baixar apenas um asset.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse

class HookCatalogError(ValueError):
    pass

VALID_CATEGORIES = {"all", "crash", "funny", "sports", "water", "animals"}
BASENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,160}\.mp4$")
CHECKSUM = re.compile(r"^[0-9a-fA-F]{64}$")

def validate_catalog(rows):
    if not isinstance(rows, list):
        raise HookCatalogError("Catálogo deve ser uma lista JSON")
    seen_names, seen_hashes = set(), set()
    for row in rows:
        if not isinstance(row, dict):
            raise HookCatalogError("Item de catálogo inválido")
        name, sha = row.get("arquivo"), row.get("sha256")
        if not isinstance(name, str) or not BASENAME.fullmatch(name):
            raise HookCatalogError("Nome de arquivo MP4 inseguro")
        if not isinstance(sha, str) or not CHECKSUM.fullmatch(sha):
            raise HookCatalogError("SHA256 ausente ou inválido")
        if name in seen_names or sha.lower() in seen_hashes:
            raise HookCatalogError("Duplicação de nome ou SHA256 no catálogo")
        seen_names.add(name)
        seen_hashes.add(sha.lower())
        if row.get("categoria") not in VALID_CATEGORIES - {"all"}:
            raise HookCatalogError("Categoria inválida no catálogo")
        try:
            duration = float(row.get("duracao_segundos"))
        except (ValueError, TypeError):
            raise HookCatalogError("Duração inválida") from None
        if not .4 <= duration <= 30:
            raise HookCatalogError("Duração MP4 fora do limite")
        origin = row.get("origem", "")
        parsed = urlparse(origin) if isinstance(origin, str) else None
        if not parsed or parsed.scheme != "https" or parsed.hostname != "viralhookup.com":
            raise HookCatalogError("Origem não autorizada")
    return rows

def choose_hook(rows, *, category="all", seed=1, recent=None):
    validate_catalog(rows)
    if category not in VALID_CATEGORIES:
        raise HookCatalogError("Categoria solicitada inválida")
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 1:
        raise HookCatalogError("Semente deve ser inteiro positivo")
    exclude = set(recent or [])
    available = sorted(
        (item for item in rows if category == "all" or item["categoria"] == category),
        key=lambda r: r["arquivo"])
    available = [item for item in available if item["arquivo"] not in exclude]
    if not available:
        raise HookCatalogError("Sem candidatos disponíveis para a categoria e histórico")
    return available[(seed - 1) % len(available)]

def main():
    cli = argparse.ArgumentParser(description="Preparar um gancho para workflow Shorts (sem renderizar)")
    cli.add_argument("--catalog", type=Path, required=True)
    cli.add_argument("--category", default="all", choices=sorted(VALID_CATEGORIES))
    cli.add_argument("--seed", type=int, default=1)
    cli.add_argument("--recent-file", type=Path)
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    rows = json.loads(args.catalog.read_text(encoding="utf-8"))
    recent = json.loads(args.recent_file.read_text(encoding="utf-8")) if args.recent_file else []
    chosen = choose_hook(rows, category=args.category, seed=args.seed, recent=recent)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(chosen, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(chosen, ensure_ascii=False))

if __name__ == "__main__":
    main()
