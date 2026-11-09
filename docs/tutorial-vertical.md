# MoneyPrint: tutoriais de tela com gancho e universo

Editor de vídeos `9:16` criado para tutoriais filmados no celular ou computador.

## Sequência visual

- **0 a 0,8 s:** gancho inesperado (ex.: quase acidente), reproduzido a **1x**. O código **não desacelera** o clipe.
- **0,8 a 3,0 s:** animação contínua do universo com título curto (preferencialmente NASA SVS).
- **A partir de 3 s:** cortes rápidos e zooms do tutorial real, **sem contador, sem legendas inferiores e sem barra superior criada pelo MoneyPrint**.
- **Privacidade:** máscaras **opacas**, aplicadas antes de zoom/resize. Nenhum áudio da gravação ou metadados pessoais são copiados.
- **Entrega:** MP4 para revisão. Sem publicação automática.

A referência original da moto foi enviada pelo usuário para comparação visual. A reutilização pública depende de autorização do titular; não versionar esse clipe na biblioteca de produção sem comprovação dos direitos de uso.

## Execução local gratuita (recomendado para arquivos privados)

Requisitos: Python 3.11+, FFmpeg/ffprobe, Pillow 11.3 e fonts-dejavu-core.

```sh
python -m pip install Pillow==11.3.0
python -m unittest discover -s tests -v

python scripts/tutorial_editor.py \
  --source "/pasta-privada/gravacao.mp4" \
  --hook-source "/pasta-privada/gancho_autorizado.mp4" \
  --universe-gif "/pasta-privada/universo.mp4" \
  --recipe tutorials/github_primeiro_repositorio.json \
  --output outputs/tutorial_vertical.mp4
```

Apesar do nome `--universe-gif`, o FFmpeg aceita **GIF animado, WebM ou MP4**. Para uso sem serviço comercial, escolha a animação da NASA:

- Fonte: https://svs.gsfc.nasa.gov/14950/ (NASA Goddard Space Flight Center/Conceptual Image Lab)
- Download direto: https://svs.gsfc.nasa.gov/vis/a010000/a014900/a014950/14950_Galaxies_FlyThrough_1080.mp4
- Cite: NASA's Goddard Space Flight Center/Conceptual Image Lab.

O pipeline **não usa APIs pagas, serviços proprietários obrigatórios nem IA local pesada**. Todo o editor funciona com FFmpeg e Pillow.

## GitHub Actions (opcional)

Workflow: `MoneyPrint — tutorial vertical (mídia revisada)`. Ele roda mediante execução manual, instala os programas gratuitos, baixa o vídeo NASA, testa o editor e entrega o MP4 em **Actions → Artifacts**.

Por segurança:
1. **Não suba gravações brutas** ou dados de conta para o GitHub, mesmo em repositório privado.
2. Primeiro remova informações pessoais localmente e confira o MP4 inteiro.
3. Somente depois coloque um arquivo **pré-anonimizado** e um gancho de uso autorizado em `assets/approved/`.
4. Informe os dois nomes de arquivos e a receita no workflow. Sem esses arquivos, a execução falha sem produzir vídeo.

A receita `tutorials/github_primeiro_repositorio.json` foi calibrada para a gravação original de 172 s (512×1108). Outras gravações exigem novos timestamps, dimensões e máscaras. **A automação não prova ausência de dados sensíveis:** revisão humana é obrigatória.

GitHub Actions utiliza cotas e políticas de cobrança próprias conforme conta/repositório. Para garantir custo operacional nulo, execute no próprio ambiente self-hosted. O workflow do GitHub é opcional.
