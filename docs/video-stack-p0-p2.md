# MoneyPrint P0–P2 — edição e motion graphics open source

O pipeline `github_cinematic` continua **slides animados primeiro**, com mockups, capturas reais, GIFs oficiais e B-roll contextual licenciado. Os modos de vídeo originais não mudam. Serviços pagos nunca são necessários: core R$ 0, self-hosted, open source.

## Implementado

| Etapa | Componente | Comportamento |
|---|---|---|
| P0 | FFmpeg / FFprobe | Normalização, MP4 H.264/AAC, cortes secos e áudio alinhado |
| P0 | Ganchos locais | Vídeo real de `assets/`, velocidade original, duração controlada, áudio original preservado |
| P0 | PySceneDetect | Lista de cortes reais `scenes` quando `scene_index=true` |
| P0 | Auto-Editor | Remove silêncios somente se `auto_cut=true` |
| P0 | OpenScreen | Exporta `.openscreen` local por CLI quando explicitamente solicitado |
| P0 | HyperFrames | Renderiza projeto HTML local por CLI quando solicitado |
| P0 | Playwright | Capturas de repositórios existentes e mockups no pipeline de slides |
| P1 | Agent Skills | Diretor de vídeo e QA de motion em `.agents/skills/` |
| P1 | Motion Canvas | Aceita clipe MP4 exportado pelo Motion Canvas como parte do storyboard |
| P1 | Transições | `cut` (padrão) ou FFmpeg xfade `fade/wipeleft/slideleft/smoothleft/circleopen` |
| P2 | Universo original | Estrelas e tipografia nítida em FFmpeg + Pillow, sem GIF travado |
| P2 | Three.js | Motor WebGL local opt-in com movimento procedural de câmera, via Chromium |

O P1 usa o `xfade` gratuito do FFmpeg (efeitos equivalentes) em vez de exigir a biblioteca externa GL Transitions. O Motion Canvas exporta MP4 para a montagem; não afirmamos que seu editor completo foi incorporado.

## Exemplo de pedido

Adicione `motion` ao pedido já válido `visual_mode: github_cinematic`:

```json
{
  "topic": "Ferramentas gratuitas para desenvolvimento",
  "visual_mode": "github_cinematic",
  "aspect": "16:9",
  "duration_seconds": 120,
  "repo_urls": ["https://github.com/appwrite/appwrite"],
  "sections": [{"repo_url":"https://github.com/appwrite/appwrite",
                "title":"Appwrite",
                "narration":"Aqui vai uma narração completa da seção com duração adequada."}],
  "motion": {
    "hook_asset": "assets/hooks/gancho-aprovado.mp4",
    "hook_seconds": 1.8,
    "universe_seconds": 1.2,
    "universe_title": "OPEN SOURCE",
    "transition": "cut",
    "scene_index": false,
    "auto_cut": false,
    "threejs": false
  }
}
```

**Atenção:** o JSON acima é um exemplo de estrutura, não um pedido de produção aprovado: o `hook_asset` deve existir; o texto de narração deve ter a duração pretendida. Notícias só são usadas se realmente verificadas. Não invente ou baixe ganchos indiscriminadamente.

## Execução local

Pré-requisitos base: Python 3.11+, FFmpeg, FFprobe, Pillow e os requisitos que o controlador existente instala. No terminal da raiz do repositório:

```bash
python3 scripts/video_stack.py --input meu-video.mp4 \
  --output resultado.mp4 --universe-seconds 1.2 \
  --universe-title "OPEN SOURCE" --transition cut
```

Ganchos precisam estar dentro de `assets/`:

```bash
python3 scripts/video_stack.py --input meu-video.mp4 \
  --hook assets/hooks/gancho-aprovado.mp4 --hook-seconds 1.8 \
  --universe-seconds 1.2 --output resultado.mp4
```

Render pelo GitHub Actions: enviar pedido novo em `requests/` ou disparar `render.yml` manualmente com `request_path`. Os arquivos ficam em `outputs/<nome-do-pedido>/`. A edição original e a versão motion coexistem, sem publicação automática.

## Adaptadores opcionais

- **PySceneDetect**: `python -m pip install "scenedetect==0.7.3"`.
- **Auto-Editor**: instalar `auto-editor` em PATH antes de ativar `auto_cut`; o áudio narrado precisa ser realinhado após cortes.
- **OpenScreen**: instalar a CLI local do projeto `getopenscreen/openscreen`, fornecer `assets/.../*.openscreen` em `openscreen_project`. Não envia a gravação a serviços externos.
- **HyperFrames**: Node 22+, `npm install -g hyperframes`, fornecer um projeto local HTML em `assets/` e configurar `hyperframes_project`. CLI executa localmente, sem serviço HeyGen pago.
- **Motion Canvas**: exportar seu vídeo como MP4 para `assets/` e informar `motion_canvas_clip`.
- **Three.js**: instalar dependência livre declarada em `motion/three-universe/package.json` com `npm install --prefix motion/three-universe --ignore-scripts`; instalar Playwright/Chromium, selecionar `threejs:true` junto de `universe_seconds>0`. Depende de WebGL (SwiftShader é permitido em runner). Se a GPU/WebGL não funcionar, use `threejs:false` para o universo FFmpeg.

Instalar adaptadores só é necessário quando seu recurso for ativado. Não há dependência de API comercial, login em serviço de vídeo ou secret novo.

## Garantia de qualidade

```bash
python -m unittest discover -s tests -v
python -m scripts.qa_video_stack --output qa-video-stack --transition cut
python -m scripts.qa_video_stack --output qa-video-stack --transition fade
```

Os workflows `test.yml` e `qa-video-stack.yml` validam contratos, arquivos MP4 reais, áudio preservado, duração, composição espacial e transições, com frames e JSON de diagnóstico nos artifacts. Antes de publicar, revisar direitos dos clipes, texto, sincronismo de legendas (especialmente após `auto_cut`), e frames finais.

**Não alterados:** secrets, OAuth, rotas, permissões, preços, workflows de publicação e modos legados.
