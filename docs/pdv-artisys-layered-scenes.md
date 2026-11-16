# PDV ArtiSys — cenas em camadas para MoneyPrint

Composição cinematográfica 9:16, 1080×1920, 30 FPS, **12 cenas / 82 segundos / 153 camadas**, sem APIs, modelos ou serviços pagos obrigatórios.

## Arquivos

- `projects/pdv-artisys-layered-v1.json`: fonte canônica da timeline; cada cena contém camadas independentes de fundo, título, texto progressivo, vídeos, etiquetas e rodapé.
- `scripts/layered_scene.py`: motor local Pillow + FFmpeg; reexporta qualquer cena de modo isolado, sem rerenderizar todo o vídeo.
- `assets/pdv/*.mp4`: os 13 clipes reais extraídos dos tutoriais próprios do ArtiSys. **Não publicar esses clipes em repositório público sem autorização.**
- `previews/pdv-01.png` etc.: prévias de composição para validar enquadramento.
- `tests/test_pdv_layered.py`: valida duração, continuidade, identificadores, textos e segurança de caminhos.

## Como executar com a pasta de projeto na raiz do MoneyPrint

```bash
python -m pip install Pillow
python -m unittest tests.test_pdv_layered -v
python -m scripts.layered_scene --input projects/pdv-artisys-layered-v1.json --root . --output outputs/pdv --preview --width 540
python -m scripts.layered_scene --input projects/pdv-artisys-layered-v1.json --root . --output outputs/pdv --scene pdv-01 --width 1080
```

Requer FFmpeg instalado. Para prévias das 12 cenas, omita `--scene`. Para renderizar todos os MP4 silenciosos, omita `--scene` e `--preview`.

## Segurança, edição e limites

- O áudio não foi gerado nem incluído nos MP4: a camada de locução Paradee está especificada como planejada, sem alegar que já foi renderizada.
- Não acessa o Google Drive em tempo de render. Instale os arquivos `assets/pdv/` do pacote privado anexado à conversa em um runner local / self-hosted antes de executar.
- A camada `background` é procedural, sem mídia de banco. A composição das telas usa somente vídeo dos tutoriais fornecidos pelo criador.
- O schema é isolado (`schema_version=1`) e **não é automaticamente editável por keyframes no painel Studio V3 atual**. A edição granular já funciona pelo JSON, sem tocar no Worker, OAuth, chaves ou login.
- O renderer não cria o MP4 final concatenado nem mixa áudio. É uma etapa de preparação de cenas independentes, como solicitado.
- Não publica em redes sociais e não dispara pipeline na `main`.
