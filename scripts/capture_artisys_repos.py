"""MoneyPrint: capture 8 *real* GitHub repository screens as independent Shorts clips.

Core: Playwright/Chromium and FFmpeg, fully self-hosted, R$ 0 / open-source.
The camera follows an actual rendered GitHub README; no generated screenshots,
paid APIs, credentials, publication, or rerender of the carousel is involved.

Example:
    python -m scripts.capture_artisys_repos --output outputs/artisys-repos --duration 8 --include-overview
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

REPOSITORIES = (
    {'name': 'ERPNext', 'slug': 'erpnext', 'url': 'https://github.com/frappe/erpnext'},
    {'name': 'Twenty CRM', 'slug': 'twenty-crm', 'url': 'https://github.com/twentyhq/twenty'},
    {'name': 'Docspell', 'slug': 'docspell', 'url': 'https://github.com/eikek/docspell'},
    {'name': 'Vaultwarden', 'slug': 'vaultwarden', 'url': 'https://github.com/dani-garcia/vaultwarden'},
    {'name': 'OpenProject', 'slug': 'openproject', 'url': 'https://github.com/opf/openproject'},
    {'name': 'Paperless-ngx', 'slug': 'paperless-ngx', 'url': 'https://github.com/paperless-ngx/paperless-ngx'},
    {'name': 'Formbricks', 'slug': 'formbricks', 'url': 'https://github.com/formbricks/formbricks'},
    {'name': 'AppFlowy', 'slug': 'appflowy', 'url': 'https://github.com/AppFlowy-IO/AppFlowy'},
)

CAPTURE_FPS = 30
VIDEO_W, VIDEO_H = 1080, 1920
_HOSTS = ('github.com', 'githubassets.com', 'githubusercontent.com')


def is_allowed_asset(host: str | None) -> bool:
    if not isinstance(host, str):
        return False
    host = host.lower()
    return any(host == suffix or host.endswith('.' + suffix) for suffix in _HOSTS)


def validate_capture_name(filename: str) -> bool:
    return isinstance(filename, str) and re.fullmatch(r'(?:0[0-9]-)[a-z0-9-]+\.mp4', filename) is not None


def build_capture_plan(*, seconds: int = 8, include_overview: bool = False) -> list[dict]:
    if type(seconds) is not int or not 5 <= seconds <= 20:
        raise ValueError('Cada captura precisa durar de 5 a 20 segundos')
    plan = []
    if include_overview:
        plan.append({'name': 'O que é GitHub', 'slug': 'github-topics',
                     'url': 'https://github.com/topics', 'file': '00-github-topics.mp4',
                     'duration_seconds': seconds, 'is_repository': False})
    for i, project in enumerate(REPOSITORIES, 1):
        plan.append({**project, 'file': f'{i:02d}-{project["slug"]}.mp4',
                     'duration_seconds': seconds, 'is_repository': True})
    for item in plan:
        u = urlsplit(item['url'])
        if u.scheme != 'https' or u.netloc != 'github.com' or u.query or u.fragment:
            raise ValueError('Apenas páginas GitHub oficiais são permitidas')
        if not validate_capture_name(item['file']):
            raise ValueError('Nome de saída não seguro')
    return plan


def _ffprobe_seconds(path: Path) -> float:
    r = subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                 '-of', 'default=noprint_wrappers=1:nokey=1', str(path)],
                                text=True, timeout=20)
    return float(r.strip())


def _run(args: list[str], *, timeout: int = 150) -> None:
    proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, timeout=timeout)
    if proc.returncode:
        raise RuntimeError('FFmpeg: ' + proc.stderr[-2200:])


def capture_report(plan: list[dict], folder: Path, errors: dict[str, str]) -> dict:
    rows = []
    for entry in plan:
        path = folder / entry['file']
        ready = path.is_file() and path.stat().st_size > 3000
        rows.append({**entry, 'status': 'captured' if ready else 'missing',
                     'bytes': path.stat().st_size if ready else 0,
                     'error': errors.get(entry['slug']),
                     'sha256': hashlib.sha256(path.read_bytes()).hexdigest() if ready else None})
    count = sum(row['status'] == 'captured' for row in rows)
    return {'status': 'complete' if count == len(rows) else 'partial', 'captured': count,
            'missing': len(rows) - count, 'clips': rows,
            'resolution': f'{VIDEO_W}x{VIDEO_H}', 'fps': CAPTURE_FPS,
            'core_paid_api_dependency': False, 'self_hosted_compatible': True,
            'autopublish': False, 'media_provenance': 'Real public GitHub page / Chromium Playwright'}


# All motion happens in the browser, on the actual page. There are no CSS mockups.
_RAF_SCROLL = r'''async ({milliseconds, isRepository}) => {
  document.documentElement.style.scrollBehavior = 'auto';
  document.body.style.scrollBehavior = 'auto';
  const marker = isRepository
    ? document.querySelector('article.markdown-body, #readme') : null;
  if (isRepository && !marker) throw new Error('README not found');
  const viewport = innerHeight;
  const maxY = Math.max(0, document.documentElement.scrollHeight - viewport);
  const readmeY = marker ? window.scrollY + marker.getBoundingClientRect().top : 0;
  const focusY = Math.max(0, Math.min(maxY, readmeY - viewport * 0.10));
  const endY = Math.max(focusY, Math.min(maxY, focusY + viewport * 1.05));
  window.scrollTo(0, 0);
  const ease = t => t * t * (3 - 2 * t);
  return await new Promise(resolve => {
    let begin = null;
    const advance = now => {
      if (begin === null) begin = now;
      const t = Math.min(1, (now - begin) / milliseconds);
      // First reveal GitHub's repository header, then explore the real README.
      const y = isRepository
        ? (t < 0.42
          ? focusY * ease(t / 0.42)
          : focusY + (endY - focusY) * ease((t - 0.42) / 0.58))
        : Math.min(maxY, viewport * 1.60) * ease(t);
      window.scrollTo(0, y);
      if (t < 1) requestAnimationFrame(advance);
      else resolve({scrollEnd: Math.round(y), readmePosition: Math.round(readmeY),
                    height: document.documentElement.scrollHeight});
    };
    requestAnimationFrame(advance);
  });
}'''


def capture_one(browser, entry: dict, output: Path) -> dict:
    """Only records page video after successful public navigation / DOM verification.

    Playwright recording begins at page creation. Trimming the tail to the exact
    motion interval removes the loading/blank portion, so no white flash leaks.
    """
    name = entry['file']
    destination = output / name
    raw_dir = output / '_webm'
    raw_dir.mkdir(parents=True, exist_ok=True)
    context = browser.new_context(
        viewport={'width': 720, 'height': 1280},
        record_video_dir=str(raw_dir), record_video_size={'width': 720, 'height': 1280},
        color_scheme='dark', device_scale_factor=1, service_workers='block',
        accept_downloads=False, reduced_motion='reduce',
    )
    context.set_default_timeout(20000)

    def guard(route):
        host = urlsplit(route.request.url).hostname
        if is_allowed_asset(host):
            route.continue_()
        else:
            route.abort()

    context.route('**/*', guard)
    page = context.new_page()
    video = page.video
    diagnostics = {}
    try:
        response = page.goto(entry['url'], wait_until='domcontentloaded', timeout=55000)
        if not response or response.status >= 400 or urlsplit(page.url).hostname != 'github.com':
            raise RuntimeError(f'Página GitHub não disponível: {entry["url"]}')
        page.wait_for_load_state('domcontentloaded')
        if entry['is_repository']:
            page.locator('article.markdown-body, #readme').first.wait_for(state='attached', timeout=20000)
        else:
            page.locator('main').first.wait_for(state='attached', timeout=20000)
        # Wait only before taking the output tail, never introduce video fake frames.
        page.wait_for_timeout(650)
        diagnostics = page.evaluate(_RAF_SCROLL, {
            'milliseconds': (entry['duration_seconds'] - 1.45) * 1000,
            'isRepository': entry['is_repository'],
        })
        page.wait_for_timeout(800)
    finally:
        context.close()
    raw = Path(video.path())
    try:
        recorded = _ffprobe_seconds(raw)
        if recorded < entry['duration_seconds'] - 0.6:
            raise RuntimeError(f'Captura WebM curta demais: {recorded:.2f}s')
        start = max(0.0, recorded - entry['duration_seconds'])
        seconds = entry['duration_seconds']
        _run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
              '-ss', f'{start:.4f}', '-i', str(raw), '-an',
              '-vf', (f'fps={CAPTURE_FPS},scale={VIDEO_W}:{VIDEO_H}:flags=lanczos,'
                      'setsar=1,tpad=stop_mode=clone:stop_duration=0.6,'
                      f'trim=duration={seconds}'),
              '-frames:v', str(seconds * CAPTURE_FPS),
              '-c:v', 'libx264', '-crf', '21', '-preset', 'veryfast',
              '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(destination)], timeout=180)
        if not destination.is_file() or destination.stat().st_size < 5000:
            raise RuntimeError('Clipes de vídeo ausentes ou muito pequenos')
        # A real preview frame for review. No fake app UI.
        _run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
              '-ss', '2.0', '-i', str(destination), '-frames:v', '1', '-q:v', '2',
              str(output / name.replace('.mp4', '.jpg'))], timeout=25)
        return {'recorded_seconds': round(recorded, 2), **diagnostics}
    finally:
        raw.unlink(missing_ok=True)


def run(plan: list[dict], output: Path, *, selected: str = 'all', force: bool = False) -> dict:
    from playwright.sync_api import sync_playwright
    output.mkdir(parents=True, exist_ok=True)
    errors = {}
    selected_plan = [row for row in plan if selected == 'all' or row['slug'] == selected]
    if not selected_plan:
        raise ValueError('Repositório não existe neste storyboard')
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for entry in selected_plan:
                target = output / entry['file']
                if not force and target.is_file() and target.stat().st_size > 3000:
                    print('CACHED:', target, flush=True)
                    continue
                print('CAPTURING:', entry['name'], entry['url'], flush=True)
                try:
                    info = capture_one(browser, entry, output)
                    print('CAPTURED:', target, info, flush=True)
                except Exception as exc:
                    errors[entry['slug']] = f'{type(exc).__name__}: {exc}'[:900]
                    print('ERROR:', entry['slug'], errors[entry['slug']], file=sys.stderr, flush=True)
        finally:
            browser.close()
    report = capture_report(plan, output, errors)
    (output / 'captures.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'captured': report['captured'],
                      'missing': report['missing']}, ensure_ascii=False), flush=True)
    return report


def main():
    ap = argparse.ArgumentParser(description='MoneyPrint GitHub Shorts — 8 real repository clips')
    ap.add_argument('--output', type=Path, default=Path('outputs/artisys-repo-captures'))
    ap.add_argument('--duration', type=int, default=8)
    ap.add_argument('--include-overview', action='store_true')
    ap.add_argument('--only', default='all', help='One project slug or all')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--plan-only', action='store_true')
    options = ap.parse_args()
    plan = build_capture_plan(seconds=options.duration, include_overview=options.include_overview)
    if options.plan_only:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return
    report = run(plan, options.output, selected=options.only, force=options.force)
    if report['status'] != 'complete':
        raise SystemExit(f'Captação parcial: {report["captured"]}/{len(plan)}; consulte captures.json')


if __name__ == '__main__':
    main()