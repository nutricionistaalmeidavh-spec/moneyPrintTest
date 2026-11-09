# MoneyPrint — vídeo P0–P2 (core R$ 0)

O modo legado de vídeo e os fluxos existentes continuam ativos. A nova montagem é **opt-in**:
adicione um objeto \`motion\` aos pedidos com \`visual_mode: github_cinematic\`.

## Recursos

| Etapa | Implementação | Condição |
| --- | --- | --- |
| P0 | FFmpeg + FFprobe, cortes secos, normalização 1080p, preservação do áudio | Core |
| P0 | 3 s (ou menos) de gancho em \`assets/\` | Ativar \`hook_asset\` |
| P0 | PySceneDetect, JSON com tempos reais de cenas | \`scene_index: true\` |
| P0 | Auto-Editor (silêncios), opt-in para não alterar narração | \`auto_cut: true\` |
| P0 | Chromium/Playwright, capturas de GitHub; OpenScreen CLI como fonte alternativa | Chromium já existente; OpenScreen pré-instalado opcional |
| P0 | HyperFrames (Apache-2.0), projeto HTML local -> MP4 | CLI instalado explicitamente, Node 22+ |
| P1 | Motion Canvas — clipe MP4 exportado pelo projeto e versionado em assets | \`motion_canvas_clip\` |
| P1 | FFmpeg xfade sem flashes brancos; corte seco é padrão | \`transition\` |
| P1 | Skills de storyboard, motion e QA (repositório) | Instruções de agentes |
| P2 | Galáxia local Pillow/FFmpeg a 30fps, sem GIF externo | \`universe_seconds\` |
| P2 | Cena espacial real em Three.js/WebGL | \`threejs: true\` + dependências locais |

**Sem APIs pagas**, login externo, autoplay de mídias desconhecidas, publicação automática
ou mudanças em OAuth/secrets. As mídias do usuário precisam estar em \`assets/\`.
Notícias só aparecem quando \`include_verified_news: true\` e há fonte verificável.

## Exemplo em pedidos JSON

Use \`docs/examples/artisys-oito-repositorios-motion-p0-p2.json\` como referência.
A configuração pode conter:

\`\`\`json
{
  "motion": {
    "hook_asset": "assets/approved/hook.mp4",
    "hook_seconds": 1.8,
    "universe_seconds": 1.2,
    "universe_title": "GITHUB EM 1 MINUTO",
    "transition": "cut",
    "scene_index": true,
    "auto_cut": false,
    "threejs": false
  }
}
\`\`\`

Este é **apenas o objeto motion**: coloque-o em um pedido \`github_cinematic\`
com \`topic\`, \`repo_urls\`, \`sections\` e outras propriedades obrigatórias.
Se \`hook_asset\` estiver presente e o arquivo não existir, o job falha claramente.

O gancho entra na velocidade original e faz corte seco para a galáxia e para o
corpo narrado. O áudio do corpo começa no ponto certo, sem reaproveitar a
narração do vídeo original nem silenciar sem consentimento. A remoção automática
de silêncios desincroniza SRT estimado e exige realinhamento antes de publicar.

## Execução local

\`\`\`bash
python -m scripts.video_stack --input entrada.mp4 --output final.mp4 \
  --universe-seconds 1.2 --aspect 16:9
python -m scripts.qa_video_stack --output qa-video-stack --transition cut
python -m scripts.qa_video_stack --output qa-video-stack --transition fade
\`\`\`

Dependências core: Python 3.11+, FFmpeg, FFprobe, Pillow. A própria integração
\`github_cinematic\` também exige Piper, Playwright e Chromium como antes.

## Adaptadores opcionais, todos locais

- **HyperFrames:** instale Node.js 22+ e \`npm install -g hyperframes@0.9.23\`.
  Configure \`hyperframes_project: "assets/meu-hyperframes"\`. Precisa de
  \`assets/meu-hyperframes/index.html\` e não usa o Studio cloud.
- **OpenScreen:** instale o CLI local e exporte projeto existente
  \`openscreen export demo.openscreen -o demo.mp4 --json\`, ou passe
  \`openscreen_project: "assets/projetos/demo.openscreen"\` para o renderizador.
  O CLI não é instalado automaticamente nos runners padrões.
- **Motion Canvas:** renderize seu projeto TypeScript com o exportador de sua
  versão e armazene o MP4 em \`assets/\`; passe \`motion_canvas_clip\`. O editor
  visual Motion Canvas não é um serviço remoto.
- **Three.js:** \`npm install --prefix motion/three-universe --ignore-scripts --no-audit --no-fund\`;
  com Playwright/Chromium instalado, \`threejs: true\` escolhe o renderizador WebGL
  local. Sem Three.js, o modo Pillow/FFmpeg continua funcionando.
- **PySceneDetect:** \`pip install scenedetect==0.7.3\`.
- **Auto-Editor:** \`pip install auto-editor\` em ambiente compatível.

Os adaptadores opcionais só são executados quando selecionados. Não é obrigatório
instalar HyperFrames, OpenScreen, Motion Canvas ou Three.js para usar o core.

## Testes e rollback

- \`python -m unittest discover -s tests -v\`
- \`python -m compileall -q scripts tests\`
- GitHub Actions: \`QA P0-P2 — cortes, áudio e motion local\`, com MP4 de exemplo.
- A PR P0–P2 pode ser revertida sem migração de banco ou alteração de secrets.
- Os vídeos são arquivos de revisão no artifact, não são publicados automaticamente.

Os jobs GitHub-hosted estão sujeitos às cotas do GitHub; self-hosted é suportado
e não há gasto por serviço comercial obrigatório.
