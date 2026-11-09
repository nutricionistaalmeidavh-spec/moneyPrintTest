"""MoneyPrint tutorial narration through MoneyPrinterTurbo's *native* TTS.

Core: self-hosted Kokoro pm_alex (pt-BR), zero paid services.
Requires MoneyPrinterTurbo and a local Kokoro-FastAPI server. No fallback.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

DEFAULT_ENDPOINT = "http://127.0.0.1:8880/v1"
ALLOWED_VOICES = frozenset({"kokoro:pm_alex", "kokoro:pm_santa"})

class VoiceError(RuntimeError):
    pass

def validate_request(text: str, voice: str, rate: float, endpoint: str) -> dict:
    if not isinstance(text,str) or not text.strip() or len(text)>3600:
        raise VoiceError("Roteiro vazio ou extenso demais")
    if voice not in ALLOWED_VOICES:
        raise VoiceError("Apenas vozes brasileiras do Kokoro self-hosted: pm_alex/pm_santa")
    if type(rate) not in (int,float) or not math.isfinite(rate) or not .90<=rate<=1.18:
        raise VoiceError("Velocidade natural permitida: 0.90–1.18 (sem narração acelerada artificial)")
    if endpoint not in ("http://127.0.0.1:8880/v1","http://localhost:8880/v1"):
        raise VoiceError("Core exclusivo self-hosted em loopback: nenhuma API comercial/externa")
    return {"script":text.strip(),"voice":voice,"rate":float(rate),"endpoint":endpoint}

def synthesize(text: str, output: Path, *, voice: str = "kokoro:pm_alex",
               rate: float = 1.08, endpoint: str = DEFAULT_ENDPOINT,
               tts_callable=None, kokoro_config=None) -> dict:
    params=validate_request(text,voice,rate,endpoint)
    output=Path(output)
    if output.suffix.lower()!=".mp3":
        raise VoiceError("Saída da função nativa MoneyPrinterTurbo precisa ser MP3")
    output.parent.mkdir(parents=True,exist_ok=True)
    if tts_callable is None or kokoro_config is None:
        try:
            from app.config import config
            from app.services import voice as mpt_voice
        except ImportError as exc:
            raise VoiceError("MoneyPrinterTurbo não instalado; instale mpt==1.3.9") from exc
        if tts_callable is None:
            tts_callable=mpt_voice.tts
        if kokoro_config is None:
            kokoro_config=config.kokoro
    # Configure ONLY the current process; never persist keys or modify OAuth.
    kokoro_config.update({"base_url":params["endpoint"],"api_key":"",
                          "model_id":"kokoro","voices":["pm_alex","pm_santa"]})
    try:
        receipt=tts_callable(params["script"],params["voice"],params["rate"],
                             str(output),voice_volume=1.0)
    except Exception as exc:
        output.unlink(missing_ok=True)
        raise VoiceError(f"MoneyPrinterTurbo Kokoro não gerou áudio: {type(exc).__name__}") from exc
    if receipt is None or not output.is_file() or output.stat().st_size<1024:
        output.unlink(missing_ok=True)
        raise VoiceError("MoneyPrinterTurbo/Kokoro indisponível: sem fallback para TTS externo")
    return {"provider":"moneyprinterturbo:kokoro","voice":params["voice"],
            "rate":params["rate"],"audio":str(output.resolve()),
            "self_hosted":True,"paid_provider_used":False}

def main():
    parser=argparse.ArgumentParser(description="TTS nativo MoneyPrinterTurbo com Kokoro local")
    parser.add_argument("--script",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    parser.add_argument("--voice",choices=sorted(ALLOWED_VOICES),default="kokoro:pm_alex")
    parser.add_argument("--rate",type=float,default=1.08)
    args=parser.parse_args()
    if not args.script.is_file() or args.script.stat().st_size>8000:
        raise VoiceError("Arquivo de roteiro inexistente ou excessivo")
    print(json.dumps(synthesize(args.script.read_text(encoding="utf-8"),args.output,
                                voice=args.voice,rate=args.rate),ensure_ascii=False,indent=2))
if __name__=="__main__":
    main()
