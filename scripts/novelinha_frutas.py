"""Prepara pacote de produção open-source para episódios da Frutalândia.

Não simula vídeo gerado: MP4 só existe após execução real do renderizador.
VoiceStudio pode gerar falas quando seu backend local estiver disponível.
"""
from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


class StoryError(ValueError):
    pass


def _valid_id(value):
    return isinstance(value, str) and bool(ID.fullmatch(value))


def validate_story(raw):
    if not isinstance(raw, dict) or not _valid_id(raw.get("id")):
        raise StoryError("ID inválido")
    fmt = raw.get("format")
    if not isinstance(fmt, dict) or fmt.get("aspect") != "9:16" or fmt.get("language") != "pt-BR":
        raise StoryError("Formato obrigatório: 9:16 e pt-BR")
    if type(fmt.get("fps")) is not int or not 12 <= fmt["fps"] <= 60:
        raise StoryError("FPS inválido")
    chars = raw.get("characters")
    if not isinstance(chars, list) or not 2 <= len(chars) <= 8:
        raise StoryError("Elenco deve conter de 2 a 8 personagens")
    cids = set()
    for c in chars:
        if not isinstance(c, dict) or not _valid_id(c.get("id")) or c["id"] in cids:
            raise StoryError("Personagem duplicado ou inválido")
        cids.add(c["id"])
        if any(not isinstance(c.get(k), str) or not 2 <= len(c[k].strip()) <= 500
               for k in ("name", "look", "voice_profile", "voice_direction")):
            raise StoryError("Descrição/voz do personagem incompleta")
    scenes = raw.get("scenes")
    if not isinstance(scenes, list) or not 2 <= len(scenes) <= 12:
        raise StoryError("Cenas devem estar entre 2 e 12")
    scene_ids = set()
    for s in scenes:
        if not isinstance(s, dict) or not _valid_id(s.get("id")) or s["id"] in scene_ids:
            raise StoryError("ID de cena inválido ou duplicado")
        scene_ids.add(s["id"])
        if type(s.get("seconds")) is not int or not 3 <= s["seconds"] <= 20:
            raise StoryError("Cena fora da duração permitida (3–20 segundos)")
        if any(not isinstance(s.get(k), str) or not 2 <= len(s[k].strip()) <= 1000
               for k in ("place", "shot", "action")):
            raise StoryError("Cena sem cenário, enquadramento ou ação")
        lines = s.get("dialogue")
        if not isinstance(lines, list) or not 1 <= len(lines) <= 6:
            raise StoryError("Cena deve ter de 1 a 6 falas")
        for line in lines:
            if not isinstance(line, dict) or line.get("speaker") not in cids:
                raise StoryError("Fala vinculada a personagem inexistente")
            if not isinstance(line.get("text"), str) or not 1 <= len(line["text"].strip()) <= 300:
                raise StoryError("Fala vazia ou extensa")
    duration = sum(s["seconds"] for s in scenes)
    if duration > 90 or duration != fmt.get("target_seconds"):
        raise StoryError("Soma das cenas deve corresponder à duração total e não ultrapassar 90 s")
    policy = raw.get("policies")
    if not isinstance(policy, dict) or policy.get("paid_providers") is not False:
        raise StoryError("Não permite provedor pago no core")
    if policy.get("auto_publish") is not False:
        raise StoryError("Publicação automática proibida")
    if policy.get("allow_voice_cloning") is not False:
        raise StoryError("Clonagem de voz não habilitada sem autorização")
    if policy.get("no_whatsapp_overlay") is not True:
        raise StoryError("Não inserir sobreposição de WhatsApp")
    return raw


def compile_story(story):
    cast = {c["id"]: c for c in story["characters"]}
    shots = []
    voices = []
    for s in story["scenes"]:
        featured = sorted({x["speaker"] for x in s["dialogue"]})
        looks = "; ".join(f'{cast[c]["name"]}: {cast[c]["look"]}' for c in featured)
        shots.append({
            "id": s["id"], "duration_seconds": s["seconds"],
            "prompt": f'{story["format"]["style"]} Cenário: {s["place"]}. '
                      f'Câmera: {s["shot"]}. Ação: {s["action"]}. '
                      f'Identidade visual fixa: {looks}',
            "acting": s["action"],
            "speakers": featured,
            "required_character_references": [
                f'assets/characters/{c}/reference.png' for c in featured],
            "source_required": "animated-characters",
            "allow_stock_substitute": False,
        })
        for i, line in enumerate(s["dialogue"], 1):
            c = cast[line["speaker"]]
            voices.append({
                "id": f'{s["id"]}-{i:02d}', "scene_id": s["id"],
                "character": c["id"], "voice": c["voice_profile"],
                "voice_direction": c["voice_direction"],
                "text": line["text"], "language": "pt-BR",
                "output": f'audio/{s["id"]}-{i:02d}.wav',
            })
    return {
        "story_id": story["id"],
        "character_bible": {
            "identity_policy": "Aparência invariável entre cenas e episódios; usar as mesmas imagens de referência.",
            "characters": story["characters"], "format": story["format"]
        },
        "openmontage": {
            "upstream": "https://github.com/calesthio/OpenMontage",
            "pipeline": "character-animation",
            "render_runtime": "hyperframes",
            "mode": "free-local", "paid_providers_enabled": False,
            "production_brief": story["title"],
            "shots": shots,
            "delivery": {"resolution": "1080x1920", "fps": story["format"]["fps"],
                         "language": "pt-BR", "captions": True, "publish": False}
        },
        "voices": voices,
        "production_status": {
            "planned": True, "voice_rendered": False, "visual_assets_rendered": False,
            "rendered": False,
            "reason": "Brief de OpenMontage não executa por si só o agente, nem gera MP4."
        },
    }


def emit_plan(plan, folder: Path):
    folder.mkdir(parents=True, exist_ok=True)
    files = {
        "openmontage-brief.json": plan["openmontage"],
        "character-bible.json": plan["character_bible"],
        "voicestudio-lines.json": plan["voices"],
        "production-status.json": plan["production_status"],
    }
    for name, content in files.items():
        (folder / name).write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n",
                                   encoding="utf-8")


def check_voice_studio_url(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost"):
        raise StoryError("VoiceStudio deve estar disponível via HTTP somente no loopback local")
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        raise StoryError("Endereço VoiceStudio inválido")
    return url.rstrip("/")


def speak_with_voice_studio(plan, folder: Path, base_url):
    """Integra VoiceStudio real. Exige perfis já criados, nunca finge dublagem."""
    base_url = check_voice_studio_url(base_url)
    req = urllib.request.Request(base_url + "/v1/audio/voices")
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            voices = json.load(response)
    except (OSError, ValueError) as exc:
        raise StoryError("VoiceStudio local não responde") from exc
    options = voices.get("data", voices) if isinstance(voices, dict) else voices
    if not isinstance(options, list):
        raise StoryError("Resposta inesperada da API de vozes do VoiceStudio")
    available = {v.get("id") for v in options if isinstance(v, dict)}
    missing = {line["voice"] for line in plan["voices"]} - available
    if missing:
        raise StoryError("Perfis VoiceStudio não cadastrados: " + ", ".join(sorted(missing)))
    for line in plan["voices"]:
        target = folder / line["output"]
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({"model": "tts-1", "voice": line["voice"],
                              "input": line["text"], "response_format": "wav"}).encode()
        post = urllib.request.Request(base_url + "/v1/audio/speech", data=payload,
                                      headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(post, timeout=180) as response:
                wav = response.read(20_000_000)
        except OSError as exc:
            raise StoryError("VoiceStudio falhou na fala " + line["id"]) from exc
        if not wav.startswith(b"RIFF") or len(wav) < 44:
            raise StoryError("VoiceStudio não devolveu áudio WAV válido para " + line["id"])
        target.write_bytes(wav)
    plan["production_status"]["voice_rendered"] = True
    (folder / "production-status.json").write_text(
        json.dumps(plan["production_status"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("story", type=Path)
    parser.add_argument("--output", type=Path, default=Path("outputs/frutalandia-plan"))
    parser.add_argument("--voicestudio-url", default="")
    args = parser.parse_args()
    try:
        plan = compile_story(validate_story(json.loads(args.story.read_text(encoding="utf-8"))))
        emit_plan(plan, args.output)
        if args.voicestudio_url:
            speak_with_voice_studio(plan, args.output, args.voicestudio_url)
    except (StoryError, OSError, ValueError) as exc:
        parser.exit(1, f"ERRO: {exc}\n")
    print(f"Pacote de produção gerado: {args.output}")


if __name__ == "__main__":
    main()
