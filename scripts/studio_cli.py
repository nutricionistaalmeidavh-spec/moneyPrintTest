"""Studio V3 local CLI: deterministic storyboard or optional reference analysis."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from scripts.studio_project import create_project, validate_project
from scripts.reference_analyzer import analyze_reference


def main() -> None:
    parser = argparse.ArgumentParser(description="MoneyPrint Studio V3 - gratuito e local")
    parser.add_argument("command", choices=["storyboard", "reference", "validate"])
    parser.add_argument("--input", required=True, type=Path, help="Roteiro TXT, vídeo ou projeto JSON")
    parser.add_argument("--output", type=Path, help="JSON de saída (exceto validate)")
    parser.add_argument("--topic")
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--aspect", choices=["9:16", "16:9", "1:1"], default="9:16")
    parser.add_argument("--assets", type=Path, help="Catálogo JSON de mídias aprovadas")
    args = parser.parse_args()
    if args.command == "validate":
        project=json.loads(args.input.read_text(encoding="utf-8"))
        validate_project(project)
        print("Projeto V3 válido")
        return
    if not args.output:
        parser.error("--output é obrigatório para storyboard e reference")
    if args.command == "reference":
        result=analyze_reference(args.input)
    else:
        text=args.input.read_text(encoding="utf-8")
        assets=json.loads(args.assets.read_text(encoding="utf-8")) if args.assets else []
        result=create_project(topic=args.topic or args.input.stem,script=text,
                              duration_seconds=args.duration,aspect=args.aspect,
                              assets=assets)
        validate_project(result)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
