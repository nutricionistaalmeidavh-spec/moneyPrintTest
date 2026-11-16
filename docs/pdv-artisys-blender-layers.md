# MoneyPrint — PDV ArtiSys em Blender 3D, entregue por camadas

**Estado verificado:** 12 cenas, 82s, 30 fps, projeto para render 9:16; 23 atuações de personagens e 21 superfícies de vídeo-textura vinculadas a 13 vídeos reais. Os 28 testes de contrato locais passaram. **Nenhum arquivo `.blend` ou MP4 Blender foi renderizado nesta sessão**: Blender não está instalado e o acesso ao download dos pacotes Standard Quaternius está bloqueado. O projeto não depende de serviços pagos.

## Direção

- Personagens: Quaternius Universal Base Characters **Standard** (CC0), modelos rigados importados, sem fallback de recortes PNG ou personagens procedurais.
- Animações: Universal Animation Library **Standard** (CC0) para movimentos-base, com keyframes adicionais em ossos para atuação: apontar, olhar, reagir, caminhar, usar celular, digitar, cozinhar, entregar prato, usar caixa, confirmar pagamento.
- Cenários: restaurante estilizado / cozinha / caixa / escritório, feitos em Blender com GLBs editáveis; câmera 3D, sombras e iluminação quente/roxa.
- Sistema: gravações **autênticas** do PDV, nos materiais de emissão das telas. O filme não deve simular, inventar ou redesenhar funcionalidades.
- Texto/CTA: 60 PNGs transparentes em camadas e dados canônicos editáveis no `timelines/typography_layers.json`.

## Estrutura do ZIP

```
assets/*.mp4                      13 tutoriais originais (somente neste ZIP privado)
assets/models/*.glb               12 objetos 3D locais reutilizáveis
projects/pdv-artisys-quaternius-v1.json       cenas, rigs, ações, câmeras, telas
projects/pdv-artisys-studio-v3-bridge.json    metadados para Studio V3; não edita ossos
scripts/rig_acting.py             18 tipos de acting em keyframes de ossos
scripts/quaternius_blender.py     importação e retarget dos rigs Standard
scripts/layered_scene.py         coleções e superfícies emissivas de vídeo
scripts/run_layered.py           render explícito no Blender local
scripts/quaternius_assets.py     instalador seguro dos ZIPs oficiais
scripts/make_overlays.py         geração de tipografia separada
scripts/create_layered_manifest.py catálogo e timeline com SHA256
scripts/create_studio_bridge.py   ponte de metadados
overlays/scene_XX/*.png          60 camadas RGBA independentes (pasta `overlays`)
timelines/scene_layers.json       projeto de composição, durações e mídia real
timelines/typography_layers.json  in/out e animação de títulos
audio/trilha-instrumental-original.m4a       trilha instrumental separada
 tests/                            testes Python sem API paga
```

## Camadas Blender por cena

| Nome da coleção | Conteúdo |
|---|---|
| `00_WORLD` | Mundo e fundo escuro |
| `10_RESTAURANT_SET` | Ambiente, piso, mesas, balcão e cozinha |
| `20_ACTORS_QUATERNIUS_CC0` | Armatures e malhas skinned por personagem, ações editáveis |
| `30_HAND_PROPS` | Celular, prato, tablet, espátula ligados ao osso da mão |
| `40_DEVICES_3D` | Notebook, monitor, celular, tablet e painel físico |
| `41_REAL_PDV_MOVIE_TEXTURES` | Superfícies emissivas usando MP4 real como `MOVIE` |
| `50_FLOATING_INFO` | Reserva para efeitos 3D contextuais opcionais |
| `60_LIGHTS` | Luz principal quente, luz de preenchimento e luz de recorte |
| `70_CAMERA` | Câmera em movimento com keyframes |
| `90_SOURCE_ANIMATIONS_HIDDEN` | Rig-fonte da biblioteca, invisível ao render |
| `95_MONEYPRINT_TEXT_OVERLAYS` | Textos separados, editados pelo MoneyPrint |
| `96_MONEYPRINT_SOUND` | Trilha original em arquivo separado; sem narração fictícia |

## Pré-requisitos gratuitos

Instale Blender 4.2+ GPL e FFmpeg no próprio computador/servidor. Baixe apenas os dois arquivos **[Standard]** gratuitos das páginas oficiais, sob licença CC0:

- https://quaternius.itch.io/universal-base-characters
- https://quaternius.itch.io/universal-animation-library

As versões pagas Source/Pro não são exigidas. Os ZIPs Quaternius não estão incluídos neste pacote, pois **não foram obtidos nesta sessão**. Não há dependência silenciosa de internet, API comercial ou assinatura.

## Importar as bibliotecas e gerar arquivos `.blend`

Execute na raiz do ZIP, com Python 3.11+:

```bash
python scripts/quaternius_assets.py \
  --characters-zip '/arquivos/Universal Base Characters[Standard].zip' \
  --animations-zip '/arquivos/Universal Animation Library[Standard].zip'
python scripts/run_layered.py --scene 05 --quality preview --posters
```

Se aprovar a cena piloto, gere as demais em camadas:

```bash
python scripts/run_layered.py --scene all --quality preview
```

Para exportar também o vídeo final de cada cena e sequências PNG transparentes de cada coleção:

```bash
python scripts/run_layered.py --scene all --quality final --render-video --render-passes
```

Saídas esperadas após **execução real do Blender**: `output/pdv_artisys_scene_01.blend` até `...12.blend`, `output/pdv_artisys_scene_XX.mp4`, `output/passes/XX/.../frame_NNNN.png`, `output/layer_manifest.json`. Para alterações pontuais, renderize apenas `--scene 07`, por exemplo.

**Aviso sobre performance:** a exportação de passes transparentes em Full HD é intencionalmente opt-in, pois gera milhares de PNGs e pode consumir muito armazenamento. Comece pelo piloto 05 em resolução preview.

## Limites documentados

- Estrutura de cenas, vídeos, duração, scripts e camadas: **criados e verificados localmente**.
- Importação real dos rigs Standard, retarget, acting e render no Blender: **ainda não executados/validados visualmente** neste ambiente.
- Os 12 GLBs do pacote são objetos de cenário, **não** os seis personagens Quaternius.
- `overlays/*.png` são tipografia independente, **não** personagens animados ou capturas falsas do PDV.
- A ponte Studio V3 é metadados; a versão atual do painel MoneyPrint **não edita keyframes de ossos nem a geometria Blender**.
- Trilha instrumental é separada; a narração Paradee permanece pendente.
- Nada publicado, nenhuma alteração automática na `main`, nenhum serviço pago ativado.

## QA

```bash
python -m unittest discover -s tests -v
python scripts/build_blender.py --project projects/pdv-artisys-quaternius-v1.json --scene 05 --dry-run --contract-only
```

Os testes checam 12 cenas contínuas, 2460 frames, 23 atuações, 21 telas, arquivos MP4, hashes, camadas de composição e isolamento de materiais originais. **Não substituem QA visual do `.blend` e dos movimentos depois do render.**
