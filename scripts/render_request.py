"""Controlador self-hosted de vídeos: GitHub Actions + MoneyPrinterTurbo + Piper + Ollama."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PIPER_MODEL = "pt_BR-faber-medium"
PIPER_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/"
PIPER_SHA256 = "858555e3a064209c57088fe6bd70c4c3dc54d03eaa00c45d5ecaf43a33f95aa7"
OLLAMA_MODEL = "qwen2.5:1.5b"
OLLAMA_IMAGE = "ollama/ollama:0.12.7"
REQUEST_PATTERN = re.compile(r"requests/[A-Za-z0-9][A-Za-z0-9_.-]{0,100}\.json\Z")
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}\Z")


class RequestError(ValueError):
    pass


def clean_terms(terms: list[str]) -> list[str]:
    if not isinstance(terms, list) or len(terms) > 12:
        raise RequestError("terms deve ser uma lista de até 12 buscas")
    unique = []
    for raw in terms:
        if not isinstance(raw, str) or not (2 <= len(raw.strip()) <= 70) or any(c in raw for c in "\r\n\x00"):
            raise RequestError("Termo de busca inválido")
        if raw.strip() not in unique:
            unique.append(raw.strip())
    return unique


def normalize_generated_terms(raw, topic: str) -> list[str]:
    """LLMs locais pequenos variam o formato; não rejeitar o pedido por formatação."""
    if isinstance(raw, str):
        items = re.split(r"[,;\n]", raw)
    elif isinstance(raw, list):
        items = raw
    else:
        items = []
    cleaned = []
    for item in items:
        if not isinstance(item, str):
            continue
        term = re.sub(r"\s+", " ", item).strip(" ,.-;")
        term = re.sub(r"[^A-Za-z0-9À-ÿ \-]", "", term).strip()[:70].strip()
        if len(term) >= 2 and term not in cleaned:
            cleaned.append(term)
        if len(cleaned) == 6:
            break
    if not cleaned:
        cleaned = ["office teamwork", "business technology", "working on laptop"]
    return cleaned


def validate_request(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise RequestError("O pedido deve ser JSON objeto")
    extra = set(raw) - {"topic", "script", "terms", "duration_seconds",
                        "aspect", "visual_mode", "repo_urls"}
    if extra:
        raise RequestError(f"Campos proibidos: {sorted(extra)}")
    topic = raw.get("topic")
    if not isinstance(topic, str) or not 1 <= len(topic.strip()) <= 280 or "\x00" in topic:
        raise RequestError("topic deve ter de 1 a 280 caracteres")
    mode = raw.get("visual_mode", "auto")
    if mode not in ("auto", "stock", "local", "pexels", "pixabay", "github"):
        raise RequestError("visual_mode inválido")
    script = raw.get("script", "")
    max_script_size = 9000 if mode == "github" else 2400
    if not isinstance(script, str) or len(script) > max_script_size or "\x00" in script:
        raise RequestError("script inválido")
    terms = clean_terms(raw.get("terms", []))
    duration = raw.get("duration_seconds", 40)
    max_duration = 360 if mode == "github" else 90
    if type(duration) is not int or not 15 <= duration <= max_duration:
        raise RequestError(f"duration_seconds deve estar entre 15 e {max_duration}")
    aspect = raw.get("aspect", "9:16")
    if aspect not in ("9:16", "16:9", "1:1"):
        raise RequestError("aspect inválido")
    repo_urls = []
    if mode == "github":
        if __package__:
            from .browser_capture import CaptureError, validate_repo_urls
        else:
            from browser_capture import CaptureError, validate_repo_urls
        try:
            repo_urls = validate_repo_urls(raw.get("repo_urls", []))
        except CaptureError as exc:
            raise RequestError(str(exc)) from exc
    elif "repo_urls" in raw:
        raise RequestError("repo_urls só pode ser usado no visual_mode github")
    return {"topic": topic.strip(), "script": script.strip(), "terms": terms,
            "duration_seconds": duration, "aspect": aspect,
            "visual_mode": mode, "repo_urls": repo_urls}


def select_visual_mode(mode: str, env: dict) -> str:
    if mode == "github":
        return "github"
    if mode == "local":
        return "local"
    if mode in {"pexels", "pixabay"}:
        if not env.get(f"{mode.upper()}_API_KEY", "").strip():
            raise RequestError(f"{mode} exige chave gratuita explícita no GitHub Secret")
        return mode
    # Padrão gratuito e sem conta/chave: Wikimedia Commons.
    return "wikimedia"


def select_requests(root: Path, *, manual="", before="", after="") -> list[Path]:
    root = root.resolve()
    if manual:
        names = [manual]
    else:
        if not COMMIT_PATTERN.fullmatch(before) or not COMMIT_PATTERN.fullmatch(after):
            raise RequestError("SHAs de push inválidos")
        changed = subprocess.run(
            ["git", "diff", "--diff-filter=A", "--name-only", before, after, "--", "requests/"],
            cwd=root, check=True, capture_output=True, text=True)
        names = changed.stdout.splitlines()
    names = sorted(set(names))
    if not 1 <= len(names) <= 4:
        raise RequestError("Envie de 1 a 4 novos pedidos por push")
    selected = []
    for name in names:
        if not REQUEST_PATTERN.fullmatch(name) or name.startswith("requests/."):
            raise RequestError("Caminho de pedido não permitido")
        path = (root / name).resolve()
        if not path.is_relative_to(root / "requests") or not path.is_file():
            raise RequestError("Arquivo JSON inexistente ou fora de requests/")
        selected.append(path)
    return selected


def build_config(template: dict, env: dict) -> dict:
    result = dict(template)
    result["app"] = dict(template.get("app", {}))
    result["whisper"] = dict(template.get("whisper", {}))
    result["app"].update({
        "llm_provider": "ollama",
        "ollama_model_name": OLLAMA_MODEL,
        "ollama_base_url": "http://127.0.0.1:11434/v1",
        "pexels_api_keys": [env["PEXELS_API_KEY"].strip()] if env.get("PEXELS_API_KEY", "").strip() else [],
        "pixabay_api_keys": [env["PIXABAY_API_KEY"].strip()] if env.get("PIXABAY_API_KEY", "").strip() else [],
        "coverr_api_keys": [], "video_source": "local",
        "subtitle_provider": "whisper", "material_concurrency": 1,
    })
    result["whisper"].update({"model_size": "tiny", "device": "cpu", "compute_type": "int8"})
    return result


def prepare_config(runtime: Path, env: dict):
    import toml
    from app.paths import config_template
    runtime.mkdir(parents=True, exist_ok=True)
    data = build_config(toml.load(config_template()), env)
    target = runtime / "config.toml"
    target.write_text(toml.dumps(data), encoding="utf-8")
    target.chmod(0o600)


def redact_log(raw: str, env: dict) -> str:
    for name in ("PEXELS_API_KEY", "PIXABAY_API_KEY"):
        secret = env.get(name, "").strip()
        if secret:
            raw = raw.replace(secret, "[REDACTED]")
    return raw


def ollama_ready():
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2) as res:
            return res.status == 200
    except (OSError, urllib.error.URLError):
        return False


def start_ollama() -> bool:
    if ollama_ready():
        return False
    subprocess.run(["docker", "run", "--rm", "-d", "--name", "moneyprint-ollama",
                    "-p", "127.0.0.1:11434:11434", OLLAMA_IMAGE],
                   check=True, capture_output=True)
    for _ in range(45):
        if ollama_ready():
            break
        time.sleep(2)
    else:
        raise RuntimeError("Ollama não iniciou")
    subprocess.run(["docker", "exec", "moneyprint-ollama", "ollama", "pull", OLLAMA_MODEL], check=True)
    return True


def target_word_count(duration: int) -> int:
    """Piper Faber PT-BR fala perto de 2,5 palavras/s no runner de QA."""
    return round(duration * 2.5)


def acceptable_script(script: str, duration: int) -> bool:
    """Rejeita resumos metalinguísticos e roteiros curtos sem inventar duração."""
    if not isinstance(script, str):
        return False
    words = re.findall(r"\b[\wÀ-ÿ]+\b", script, flags=re.UNICODE)
    desired = target_word_count(duration)
    if len(words) < desired * 0.83 or len(words) > desired * 1.35:
        return False
    normalized = script.casefold().lstrip(' "\\n')
    return not normalized.startswith((
        "o script ", "este script ", "o roteiro ", "este roteiro ",
        "o texto ", "este texto ", "a resposta ",
    ))


def generate_text(topic: str, duration: int) -> dict:
    desired = target_word_count(duration)
    for attempt in range(3):
        prompt = (
            "Você é um roteirista brasileiro profissional de vídeos curtos. "
            "Escreva o TEXTO COMPLETO falado pelo narrador diretamente ao público, "
            "em português brasileiro natural, com abertura envolvente, 2-3 dicas úteis "
            "e fechamento. Não descreva o roteiro, não diga 'o script aborda', "
            "não explique o que vai fazer e não inclua marcações ou títulos. "
            "Não invente preços, dados estatísticos ou fatos específicos. "
            f"TEMA: {topic}. DURAÇÃO: {duration} segundos. "
            f"OBRIGATÓRIO: o texto falado deve ter ENTRE {round(desired * .9)} E "
            f"{round(desired * 1.15)} PALAVRAS, conte as palavras antes de responder. "
            "Retorne APENAS JSON válido com 'script' (fala completa) e 'terms' "
            "(4 termos curtos de pesquisa em inglês para vídeos de apoio). "
            f"Esta é a tentativa {attempt + 1}; não entregue um resumo."
        )
        data = json.dumps({
            "model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
            "format": "json", "options": {"temperature": 0.35,
                                           "num_predict": min(4200, max(1000, desired * 3))}
        }).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate", data=data,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=420) as res:
            reply = json.load(res)
        try:
            generated = json.loads(reply["response"])
        except (ValueError, TypeError, KeyError):
            continue
        if isinstance(generated, dict) and acceptable_script(generated.get("script", ""), duration):
            return generated
    raise RequestError(
        "O modelo local não gerou roteiro na duração solicitada após 3 tentativas; "
        "para manter qualidade, a renderização foi interrompida sem criar vídeo curto."
    )


def local_slides(topic: str, folder: Path, aspect: str) -> list[str]:
    from PIL import Image, ImageDraw, ImageFont
    folder.mkdir(parents=True, exist_ok=True)
    w, h = {"9:16": (720, 1280), "16:9": (1280, 720), "1:1": (900, 900)}[aspect]
    fpath = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    def font(sz):
        return ImageFont.truetype(fpath, sz) if Path(fpath).exists() else ImageFont.load_default()
    images = []
    for i, label in enumerate(["FERRAMENTAS GRATUITAS", topic, "ARTISYS • OPEN SOURCE"]):
        colors = [(12, 22, 42), (12, 43, 60), (17, 35, 52)]
        canvas = Image.new("RGB", (w, h), colors[i])
        draw = ImageDraw.Draw(canvas)
        draw.rectangle((0, 0, w, 12), fill=(0, 195, 180))
        draw.rounded_rectangle((int(w*.05), int(h*.32), int(w*.95), int(h*.7)),
                               radius=22, outline=(0, 195, 180), width=3, fill=(25, 46, 67))
        draw.text((int(w*.07), int(h*.13)), "ARTISYS   /   SEM MENSALIDADE",
                  font=font(int(w*.029)), fill=(110, 235, 217))
        lines, current = [], ""
        for word in label.upper().split():
            trial = (current + " " + word).strip()
            if len(trial) > 24 and current:
                lines.append(current)
                current = word
            else:
                current = trial
        if current:
            lines.append(current)
        lines = lines[:8]
        face = font(int(w*.05))
        for j, line in enumerate(lines):
            measured = draw.textbbox((0, 0), line, font=face)
            draw.text((max(12, (w-measured[2]+measured[0])//2),
                       int(h*.49)-(len(lines)*int(w*.04))+j*int(w*.08)),
                      line, font=face, fill=(244, 250, 252))
        target = folder / f"scene_{i+1}.jpg"
        canvas.save(target, quality=90)
        images.append(str(target.resolve()))
    return images


def download_piper(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    model = folder / (PIPER_MODEL + ".onnx")
    config = folder / (PIPER_MODEL + ".onnx.json")
    if not model.exists() or hashlib.sha256(model.read_bytes()).hexdigest() != PIPER_SHA256:
        tmp = folder / "voice.tmp"
        digest = hashlib.sha256()
        try:
            with urllib.request.urlopen(PIPER_BASE + model.name, timeout=90) as res, tmp.open("wb") as out:
                while data := res.read(1024*1024):
                    digest.update(data)
                    out.write(data)
            if digest.hexdigest() != PIPER_SHA256:
                raise RuntimeError("Verificação SHA256 do modelo Piper falhou")
            tmp.replace(model)
        finally:
            tmp.unlink(missing_ok=True)
    if not config.exists():
        with urllib.request.urlopen(PIPER_BASE + config.name, timeout=60) as res:
            config.write_bytes(res.read(100000))
    return model


def build_manifest(req, script, terms, source, audio_path, media):
    task = {
        "video_subject": req["topic"], "video_script": script,
        "video_terms": terms, "video_language": "pt-BR",
        "video_aspect": req["aspect"], "video_source": source,
        "voice_name": "no-voice", "custom_audio_file": audio_path,
        "video_count": 1, "video_clip_duration": 5,
        "bgm_type": "", "bgm_volume": 0, "subtitle_enabled": True,
        "video_concat_mode": "sequential", "n_threads": 2
    }
    if req.get("visual_mode") == "github":
        count = len(req["repo_urls"])
        task["video_clip_duration"] = min(60, max(8, (req["duration_seconds"] + count - 1) // count))
    if source == "local":
        task["video_materials"] = [{"provider": "local", "url": p, "duration": 0} for p in media]
    return task


def load_request(path):
    if path.stat().st_size > 32768:
        raise RequestError("Pedido acima de 32 KB")
    return validate_request(json.loads(path.read_text(encoding="utf-8")))


def render_one(path: Path, output: Path, runtime: Path, env: dict):
    data = load_request(path)
    dest = output / path.stem
    dest.mkdir(parents=True, exist_ok=True)
    source = select_visual_mode(data["visual_mode"], env)
    script, terms = data["script"], data["terms"]
    started_ollama = False
    try:
        if not script or not terms:
            started_ollama = start_ollama()
            generated = generate_text(data["topic"], data["duration_seconds"])
            if not script:
                script = generated.get("script", "")
            if not terms:
                terms = normalize_generated_terms(generated.get("terms"), data["topic"])
        script_limit = 9000 if data["visual_mode"] == "github" else 2400
        if not isinstance(script, str) or not script.strip() or len(script) > script_limit or not terms:
            raise RequestError("Roteiro ou termos não produzidos pelo modelo local")
        script = script.strip()
        (dest / "roteiro.txt").write_text(script, encoding="utf-8")
        voice = download_piper(runtime / "piper-model")
        audio = dest / "narracao.wav"
        subprocess.run(["piper", "--model", str(voice), "--output_file", str(audio)],
                       input=script, text=True, check=True, capture_output=True)
        if not audio.is_file() or audio.stat().st_size < 256:
            raise RuntimeError("Piper não produziu áudio")
        material_source = source
        if source == "github":
            if __package__:
                from .browser_capture import capture_repositories
            else:
                from browser_capture import capture_repositories
            materials = capture_repositories(data["repo_urls"], data["duration_seconds"],
                                             dest / "browser")
            material_source = "github_desktop"
            source = "local"
        elif source == "wikimedia":
            if __package__:
                from .commons_media import find_free_videos
            else:
                from commons_media import find_free_videos
            materials, records = find_free_videos(terms, dest)
            if materials:
                material_source = "wikimedia"
            elif data["visual_mode"] == "stock":
                raise RequestError(
                    "Wikimedia Commons não retornou vídeos com licença permitida; "
                    "use visual_mode=auto para fallback em artes locais")
            else:
                print("Aviso: sem vídeos adequados no Commons; criando artes originais.", flush=True)
                materials = local_slides(data["topic"], dest / "slides", data["aspect"])
                material_source = "artes_locais_fallback"
            source = "local"  # MPT recebe vídeos/figuras baixados como mídia local.
        elif source == "local":
            materials = local_slides(data["topic"], dest / "slides", data["aspect"])
        else:
            materials = []
        manifest = build_manifest(data, script, terms, source, str(audio.resolve()), materials)
        manifest_file = dest / "manifest.json"
        manifest_file.write_text(json.dumps([manifest], ensure_ascii=False, indent=2), encoding="utf-8")
        cmd = ["mpt", "cli", "--batch-file", str(manifest_file.resolve()), "--stop-at", "video"]
        run = subprocess.run(cmd, text=True, capture_output=True, timeout=70*60,
                             env={**env, "MPT_HOME": str(runtime.resolve())})
        (dest / "mpt-stderr.log").write_text(redact_log(run.stderr[-25000:], env), encoding="utf-8")
        if run.returncode:
            raise RuntimeError(f"MoneyPrinterTurbo falhou (exit {run.returncode})")
        try:
            summary = json.loads(run.stdout.strip().splitlines()[-1])
            task = summary["tasks"][0]
            if summary["failed"] or task["status"] != "succeeded":
                raise RuntimeError("MPT reportou falha")
            videos = task["result"].get("videos") or task["result"].get("combined_videos") or []
        except (ValueError, KeyError, TypeError, IndexError) as exc:
            raise RuntimeError("Resposta JSON do MPT inválida") from exc
        if not videos:
            raise RuntimeError("MPT não informou MP4 de saída")
        for i, video in enumerate(videos[:4], start=1):
            video_file = Path(video)
            if not video_file.is_file() or video_file.suffix.lower() != ".mp4":
                raise RuntimeError("MP4 esperado não encontrado")
            shutil.copy2(video_file, dest / f"video_{i}.mp4")
        (dest / "resultado.json").write_text(
            json.dumps({"status": "success", "topic": data["topic"], "visual_source": material_source,
                        "upstream": "harry0703/MoneyPrinterTurbo mpt==1.3.9"},
                       ensure_ascii=False, indent=2), encoding="utf-8")
    finally:
        if started_ollama:
            subprocess.run(["docker", "stop", "moneyprint-ollama"], check=False, capture_output=True)


def main():
    parser = argparse.ArgumentParser(description="MoneyPrintTest no GitHub Actions")
    parser.add_argument("--manual", default=os.getenv("REQUEST_PATH", ""))
    parser.add_argument("--before", default=os.getenv("PUSH_BEFORE", ""))
    parser.add_argument("--after", default=os.getenv("PUSH_AFTER", ""))
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    output = root / "outputs"
    runtime = Path(os.getenv("MPT_HOME", str(root / ".runtime")))
    try:
        for path in select_requests(root, manual=args.manual, before=args.before, after=args.after):
            print(f"Renderizando pedido: {path.name}", flush=True)
            try:
                prepare_config(runtime, os.environ)
                render_one(path, output, runtime, os.environ)
            except Exception as exc:
                dest = output / path.stem
                dest.mkdir(parents=True, exist_ok=True)
                (dest / "erro.txt").write_text(redact_log(f"{type(exc).__name__}: {exc}", os.environ),
                                                 encoding="utf-8")
                raise
        return 0
    except (RequestError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        print("ERRO: " + redact_log(str(exc), os.environ), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
