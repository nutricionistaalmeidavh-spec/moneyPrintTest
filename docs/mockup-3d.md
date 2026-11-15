# Mockups 3D reais no MoneyPrint (opt-in, R$ 0)

Implementação: `tools/mockup-catalog/index.html` (Three.js, MIT),
`tools/mockup-catalog/scene.mjs` (geometrias + textura de vídeo) e
`scripts/mockup_3d.py` (Playwright + FFmpeg).

O renderizador principal do Studio V3 continua usando Pillow/FFmpeg;
**não instala Three.js nem Playwright adicionais para cenas comuns**.
Nada usa API paga, CDN, token ou mídia externa. A origem e a licença dos vídeos
continuam sendo responsabilidades do criador e do catálogo canônico.

## Prévia visual local

```bash
npm install --prefix tools/mockup-catalog --ignore-scripts --no-audit --no-fund
python -m http.server 8000
```

Acesse http://127.0.0.1:8000/tools/mockup-catalog/ e selecione um vídeo MP4/WebM no seu dispositivo.
A gravação fica na memória do navegador, sem upload. O notebook e o monitor
são geometrias tridimensionais (WebGL), não uma imagem plana CSS.

## Gerar MP4 determinístico

É necessário ter Python 3.11+, FFmpeg, Playwright Chromium e Node.js 22+ instalados localmente.

```bash
python -m pip install playwright==1.56.0
python -m playwright install chromium
python -m scripts.mockup_3d \
  --input assets/captura.mp4 \
  --output outputs/notebook-vertical.mp4 \
  --device laptop --motion orbit --aspect 9:16 --fps 30 --frames 120
```

Parâmetros: `--device laptop|monitor`,
`--motion enter|orbit|zoom|float`,
`--aspect 16:9|9:16|1:1`. As dimensões padrão são 1920×1080,
1080×1920 e 1080×1080. `--width`/`--height` permitem QA de baixo custo.
O sistema renderiza um quadro por tempo, sem depender da velocidade da máquina.
O arquivo resultante é silencioso; o Studio V3 adiciona a narração ao compor a cena.

## Utilização no Studio V3

No editor de cenas, escolha **Notebook / monitor 3D com vídeo real**,
selecione um dispositivo, movimento e associe **mídia aprovada** do catálogo.

Exemplo de trecho de cena canônica:

```json
{
  "id": "scene-001",
  "track_id": "video",
  "title": "Demonstração do software",
  "text": "Observe a interface real dentro do notebook.",
  "kind": "media",
  "asset_id": "captura-real",
  "start_frame": 0,
  "duration_frames": 120,
  "layout": "device_mockup_3d",
  "mockup_device": "laptop",
  "mockup_motion": "enter",
  "animation": "cut"
}
```

O item `captura-real` precisa existir em `assets[]` do projeto com
`path: "assets/captura.mp4"`, licença, origem e `verified: true`;
o arquivo físico deve existir no runner, em `assets/`. O renderizador não
faz upload de gravações por conta própria. O CI do Studio instala Three.js
somente quando o storyboard contém esse layout.

**Não confundir:** a prévia gráfica do painel Studio é um storyboard; para
prévia WebGL real use o catálogo local acima. O resultado final 3D aparece no
MP4 do workflow `studio-render.yml` após o merge.

## QA

A PR executa `.github/workflows/qa-mockup-3d.yml`: contrato Python,
sintaxe JavaScript, sincronização dos assets do Worker, render de notebook
e monitor com um clipe artificial (sem direitos autorais), e validação de
quadros com FFprobe. Os MP4s de QA ficam nos artifacts e não são publicados
automaticamente. Em máquina sem suporte a WebGL/Chromium, o adaptador falha
explicitamente; não substitui a renderização por uma falsa simulação.
