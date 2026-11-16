# MoneyPrint — pacote Blender P0/P1 (experimental)

Este diretório contém código para montar 12 cenas Blender com rigs e capturas **reais** do PDV ArtiSys nas superfícies dos dispositivos. A arte final não foi renderizada em Blender neste ambiente porque o binário não estava instalado; executar primeiro o piloto 05 e fazer QA visual.

O arquivo `projects/pdv-artisys-blender-v1.json` descreve 82 segundos / 2460 quadros, 22 instâncias de 6 papéis, 12 modelos de objetos geráveis e 11 vídeo-texturas.

## Contrato público / contrato privado

**Não incluir o conteúdo de `assets/*.mp4` no repositório público.** O operador fornece os MP4 originais por meio do pacote privado no executor self-hosted. `--contract-only --dry-run` valida a estrutura sem esses arquivos, mas **não** renderiza nem certifica que as mídias estão disponíveis.

```bash
python scripts/blender_pdv/build_blender.py --contract-only --dry-run --scene all
python -m unittest discover -s tests -p 'test_blender_contract_repo.py' -v

# No executor que possui os arquivos originais em assets/
blender -b --python scripts/blender_pdv/build_blender.py -- --scene 05 --still --quality preview
blender -b --python scripts/blender_pdv/build_blender.py -- --scene 05 --animate --quality preview
```

Depois de validar o piloto, renderizar as outras 11 cenas com `scripts/render_and_join.py`. FFprobe deve confirmar frames e 30fps. A composição final e a narração ficam no MoneyPrint, sem publicação automática. Nenhum serviço pago é necessário.

**Limite artístico:** o rig procedural é protótipo de execução; personagens 3D premium exigem substituição por humanoides CC0 realmente rigados e retarget de movimentos. Sugeridos: Quaternius Universal Base Characters (CC0) e Universal Animation Library Standard (CC0); a versão Source/Pro é opcional paga e não deve ser exigida.
