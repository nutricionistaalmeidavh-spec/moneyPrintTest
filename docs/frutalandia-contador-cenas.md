# Frutalândia — EP01: O Contador do Butico

Este episódio é independente de `O Áudio de Amanhã` e do workflow MoneyPrinterTurbo. A produção usa **Blender 3D + Piper + FFmpeg**; OpenMontage continua apenas como contrato de planejamento, e VoiceStudio somente funciona quando um servidor local real e perfis estiverem disponíveis. Não são utilizados APIs pagas por padrão.

## Arquivos

- `stories/frutalandia/contador-do-butico-ep01.json`: seis cenas de oito segundos, quatro personagens adultos, falas de humor e sotaque nordestino, contadores **000 / 007 / 038 / 999+**, no desfecho **ERR**.
- `scripts/frutalandia_blender.py`: forma a feira livre, as frutas animadas, a tipografia 3D na testa e renderiza apenas a faixa de quadros `FRUTALANDIA_SCENE_ID=s01..s06`.
- `scripts/frutalandia_episode_runner.py --scene-id s02`: renderiza uma cena com narração, legendas e MP4; o job falha se MP4 real não for gerado.
- `scripts/frutalandia_kaggle_bundle.py --scene-id s02 --slug butico-ep01-s02`: prepara notebook Kaggle **privado**, sem incorporar credenciais no código.
- `scripts/frutalandia_scenes.py`: verifica duração, vídeo H.264, áudio AAC, 720×1280, presença das seis cenas e monta o MP4 final com FFmpeg.

## Workflow 1: seis cenas independentes

**Frutalândia — Contador, seis cenas na GPU** (`.github/workflows/frutalandia-scenes.yml`)

- `scene=all`: inicia seis jobs independentes, `s01..s06`, em **sequência** (`max-parallel: 1` para respeitar cotas gratuitas do Kaggle).
- `scene=s03`: reprocessa somente a cena 3; entrega artifact `fruit-scene-s03`.
- `scene=s03` com `base_run_id=<ID de execução anterior com todos os clips>`: reprocessa a cena 3, reaproveita os demais MP4s da execução base e remonta o episódio.
- Cada cena usa um kernel privado distinto `butico-ep01-s01` a `butico-ep01-s06`; GPU T4 somente quando a conta gratuita estiver elegível.
- Só entra na montagem quando as seis cenas estiverem disponíveis. Não há fallback por estoque/imagens estáticas.
- O artifact final é `frutalandia-contador-ep01-<run_id>`, contendo `frutalandia-contador-ep01.mp4`, `manifest.json`, `capa.png`.
- `KAGGLE_API_TOKEN` é lido do GitHub Secret existente sem alteração ou vazamento.

## Workflow 2: remontagem manual sem GPU

**Frutalândia — remontar episódio existente** (`.github/workflows/frutalandia-assemble.yml`) recebe `source_run_id`. Reúne as seis cenas produzidas numa execução anterior e valida o resultado com FFprobe, sem consumir cota Kaggle.

## Qualidade e limites

- Render nativo procedural Blender 360×640 em 12 FPS, convertido por FFmpeg para 720×1280/24 FPS: não é IA generativa Wan, não é resolução nativa 720p.
- Piper é a voz gratuita padrão em pt-BR; entonação nordestina precisa ser avaliada auditivamente — não há garantia automática de sotaque perfeito.
- O OpenMontage é uma especificação auxiliar, não executado nesta Action.
- A opção de reprocessamento por cena depende dos artifacts disponíveis da execução base (retenção de sete dias).
- Se GPU Kaggle indisponível, cota excedida ou falha técnica, a Action **falha e informa o motivo**, sem marcar episódio como renderizado.
- Por padrão: **sem merge na main, sem publicação automática, sem API paga, sem mudança em secrets**.

## Validar localmente

```bash
python -m unittest discover -s tests -v
python -m scripts.frutalandia_scenes validate --story stories/frutalandia/contador-do-butico-ep01.json
```
