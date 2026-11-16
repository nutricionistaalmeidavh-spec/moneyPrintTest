# MoneyPrint PDV — Etapa 5: piloto 05, mídia real e QA de camadas

**Status verificado:** o filme da tela do cardápio está limpo e pronto para ser aplicado como textura MOVIE em Blender. O vídeo de 7 segundos foi feito com dois recortes de gravação autêntica do PDV (3–6s e 12–16s), sem redesenhar a interface. O material tem 210 frames a 30 FPS em 1080×1920 e não possui áudio.

**Blender 3D ainda NÃO foi executado:** Blender não está instalado no ambiente, os arquivos Standard da Quaternius não estão presentes e a rede do container está indisponível. Por isso não há `.blend` nem MP4 3D novo; os testes locais não constituem validação visual de acting/iluminação.

## Camadas e modificações
- `assets/cliente-qr-cena05-clean.mp4`: recorte de vídeo real de dentro do celular, sem legendas grandes do tutorial.
- `projects/pdv-artisys-quaternius-stage5.json`: versão opt-in; cena 05 usa a textura limpa e preserva a origem. O projeto canônico anterior permanece sem modificações.
- `scripts/layered_scene.py`: passes independentes preservam câmeras e luzes; câmeras/luzes não são exportadas como passes vazios.
- `scripts/screen_reel_05.py`: receita reprodutível do recorte FFmpeg; exige fonte real.
- `qa/pilot05_contact.png`: evidência visual de quadros reais extraídos da textura limpa.
- `qa/real_screen_source.json`: hash da origem, hash da derivação e tempo dos recortes.
- `tests/test_stage5.py`: QA automatizado do material e correção dos passes.

## Executar em ambiente Blender self-hosted, após instalar as duas bibliotecas Standard (CC0)

```bash
python scripts/quaternius_assets.py \
  --characters-zip '/sua-pasta/Universal Base Characters[Standard].zip' \
  --animations-zip '/sua-pasta/Universal Animation Library[Standard].zip'
python scripts/run_layered.py --scene 05 --quality preview --posters --project projects/pdv-artisys-quaternius-stage5.json
python scripts/run_layered.py --scene 05 --quality final --render-video --render-passes --project projects/pdv-artisys-quaternius-stage5.json
```

A ausência de Blender ou de qualquer Standard gera falha explícita, **sem fallback para personagens PNG ou serviço pago**. Nenhuma publicação foi autorizada.

## Verificação local

```bash
python -m unittest discover -s tests -v
python scripts/build_blender.py --project projects/pdv-artisys-quaternius-v1.json --scene 05 --dry-run --contract-only
```

O render Blender será a prova visual obrigatória antes de considerar a etapa de atuação finalizada.
