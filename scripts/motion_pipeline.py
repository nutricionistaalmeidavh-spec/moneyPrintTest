"""New MoneyPrint pipeline: animated slides first, real-media inserts second.

Replaces the unsuccessful full-screen screen-recording aesthetic for the
github_cinematic mode. Does not ingest or re-encode any frame of the old MOV.
"""
from __future__ import annotations
import json
import subprocess
from pathlib import Path

from scripts.animated_slides import render_animated_section
from scripts.repo_stills import capture_repo_stills
from scripts.ai_director import (
    official_repo_image, official_repo_gif, fetch_news_headline,
    suggest_broll_query
)
from scripts.commons_media import find_free_videos, source_credits

# When B-roll is appropriate, search for the human situation, not footage of
# someone's monitor or screen. Missing footage does not stop the video.
CONTEXTUAL_SEARCHES = {
    "appwrite": "office team collaboration",
    "payload": "editing newspaper print",
    "flowise": "warehouse automation robot",
    "docling": "office document scanner",
    "meilisearch": "retail store checkout",
    "keycloak": "building access card security",
    "novu": "telephone incoming message",
    "infisical": "data center servers",
}


def duration_of(path:Path)->float:
    return float(subprocess.check_output(
        ["ffprobe","-v","error","-show_entries","format=duration",
         "-of","default=noprint_wrappers=1:nokey=1",str(path)],
        text=True,timeout=30).strip())


def _render_motion_base(request:dict,dest:Path,runtime:Path,env:dict)->dict:
    from scripts.render_request import download_piper
    from scripts.cinematic_render import estimate_subtitles,write_srt

    sections=request["sections"]
    urls=request["repo_urls"]
    dest.mkdir(parents=True,exist_ok=True)
    stills=capture_repo_stills(urls,dest/"github_stills")
    if len(stills)!=len(sections):
        raise RuntimeError("Capturas de projetos incompletas")

    # Piper is open-source and runs in the Actions container; no premium API.
    voice_model=download_piper(runtime/"piper-model")
    final_clips=[]
    reports=[]
    credit_lines=["MoneyPrint / ArtiSys — proveniência das imagens e vídeos",
                  "GitHub: screenshots do Chromium/Playwright dos repositórios públicos.",
                  "As capturas foram enquadradas dentro de mockups; não são vídeos antigos.",
                  ""]
    media_records=[]
    subtitle_cues=[]
    timeline_seconds=0.0
    for i,section in enumerate(sections,1):
        folder=dest/f"secao_{i:02d}"
        folder.mkdir(exist_ok=True)
        voice=folder/"narracao.wav"
        subprocess.run(["piper","--model",str(voice_model),"--output_file",str(voice)],
                       input=section["narration"],text=True,capture_output=True,
                       check=True,timeout=200)
        voice_seconds=duration_of(voice)
        if voice_seconds < 3:
            raise RuntimeError(f"Narração vazia: {i}")
        screenshots=list(stills[i-1])
        credit_lines.append(f"{i}. {section['title']} | {section['repo_url']}")

        original_screenshot=official_repo_image(section["repo_url"],
                                                folder/"official")
        if original_screenshot:
            screenshots.insert(0,original_screenshot)
            credit_lines.append("    Captura oficial: README do repositório")

        # Real GIF when the project's own README publishes one.
        media=[]
        demo=official_repo_gif(section["repo_url"],folder/"official_demo")
        if demo:
            media.append({"kind":"official_demo","path":demo})
            credit_lines.append("    GIF original do README oficial (convertido a MP4)")

        # User-selected videos may be anything; there is no arbitrary editorial
        # ban. Constrain the file path to the existing assets directory.
        for provided in request.get("media_clips",[]):
            if provided["repo_index"] != i: continue
            root=(Path.cwd()/"assets").resolve()
            candidate=(Path.cwd()/provided["path"]).resolve()
            if not candidate.is_relative_to(root) or not candidate.is_file():
                continue
            if candidate.suffix.lower() in (".mp4",".mov",".webm"):
                media.append({"kind":"user_media","path":str(candidate)})
                credit_lines.append(f"    Mídia fornecida: {provided['path']}")

        # Only add stock if real copyrighted/license metadata is available.
        if not media:
            slug=section["repo_url"].rstrip("/").split("/")[-1].casefold()
            term=CONTEXTUAL_SEARCHES.get(
                slug, section.get("broll_query","people working in office"))
            try:
                found,records=find_free_videos([term],folder/"licensed_stock",
                                               max_results=1)
                for clip,record in zip(found,records):
                    media.append({"kind":"contextual_video","path":clip})
                    media_records.append({"repo":section["repo_url"],"source":record})
                if records: credit_lines.append(source_credits(records))
            except (OSError,ValueError,subprocess.SubprocessError) as exc:
                print(f"B-roll da seção {i} indisponível: {type(exc).__name__}",
                      flush=True)

        # News is optional and has its one hard editorial rule: real provenance.
        # A weak/unavailable RSS result becomes NO NEWS, not a generated card.
        if request.get("include_verified_news",False):
            news=fetch_news_headline(section["repo_url"])
            if news:
                from scripts.cinematic_render import make_news_card
                card=folder/"real_news.png"
                make_news_card(card,news)
                screenshots.append(str(card))
                credit_lines.append(f"    Notícia verificada: {news['headline']} "
                                    f"| {news['publisher']} | "
                                    f"{news['published_at']} | {news['url']}")
                media_records.append({"repo":section["repo_url"],
                                      "news":news})

        report=render_animated_section(
            section,i,len(sections),voice,voice_seconds,folder,
            screenshots=screenshots,media=media)
        final_clips.append(Path(report["video"]))
        subtitle_cues.extend(estimate_subtitles(
            section["narration"],timeline_seconds,voice_seconds))
        timeline_seconds += duration_of(final_clips[-1])
        reports.append(report)
        print(f"Slides animados {i}/{len(sections)}: "
              f"{section['title']} {voice_seconds:.1f}s",flush=True)

    playlist=dest/"chapters.txt"
    playlist.write_text("".join(f"file '{clip.resolve()}'\n"
                                for clip in final_clips),encoding="utf-8")
    output=dest/"video_1.mp4"
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin",
                    "-y","-f","concat","-safe","0","-i",str(playlist),
                    "-c","copy","-movflags","+faststart",str(output)],
                   check=True,timeout=600)
    write_srt(dest/"legendas_estimadas.srt",subtitle_cues)
    (dest/"creditos.txt").write_text("\n".join(credit_lines),encoding="utf-8")
    (dest/"licencas_midia.json").write_text(
        json.dumps(media_records,ensure_ascii=False,indent=2),encoding="utf-8")
    (dest/"storyboard_animado.json").write_text(
        json.dumps(reports,ensure_ascii=False,indent=2),encoding="utf-8")
    (dest/"roteiro.txt").write_text(
        "\n\n".join(s["narration"] for s in sections),encoding="utf-8")
    result={"status":"success","style":"animated_slides_v2",
            "source_video_reused":False,"news_policy":"only_verified",
            "sections":len(reports),"duration_seconds":duration_of(output),
            "output":str(output)}
    (dest/"resultado.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    return result


def render_motion_first(request:dict,dest:Path,runtime:Path,env:dict)->dict:
    """Preserve animated-slides v2 from main, then opt into P0-P2 post-production."""
    from scripts.video_stack import normalize_motion_options, render_stack
    opts = normalize_motion_options(request.get("motion", {}))
    result = _render_motion_base(request, dest, runtime, env)
    active = (opts["hook_asset"] is not None or opts["universe_seconds"]>0
              or opts["auto_cut"] or opts["scene_index"]
              or opts["hyperframes_project"] or opts["openscreen_project"]
              or opts["motion_canvas_clip"])
    if not active:
        return result
    original = Path(result["output"])
    if not original.is_file():
        raise RuntimeError("Pipeline animado não produziu MP4")
    updated = render_stack(original, dest/"video_1_motion.mp4",
                           options=opts, assets=Path.cwd()/"assets")
    merged = dict(result)
    merged["original_output"] = str(original)
    merged["output"] = updated["output"]
    merged["duration_seconds"] = updated["duration_seconds"]
    merged["motion_stack"] = updated
    if opts["auto_cut"]:
        merged["subtitle_note"] = "Recrie o SRT após cortes automáticos; tempos antigos inválidos"
    (dest/"resultado.json").write_text(
        json.dumps(merged,ensure_ascii=False,indent=2),encoding="utf-8")
    return merged
