# MoneyPrint — tutoriais a partir de gravações de tela

Editor adicional e isolado para transformar uma gravação real de tela em vídeo curto vertical com gancho, cortes rápidos, legendas de passo, tela de encerramento e áudio original gerado localmente.

**Gravações privadas não devem ser commitadas em um repositório público.** Este modo usa **um MP4 local** e uma receita JSON versionável. O fluxo de vídeos tradicional do MoneyPrint (Piper/Whisper/MoneyPrinterTurbo/Playwright) não é modificado.

## Dependências gratuitas
- Python 3.11+
- FFmpeg e ffprobe
- Pillow: \`python -m pip install Pillow\`
- Linux com fonte DejaVu Sans Bold (instalar \`fonts-dejavu-core\` se necessário)

## Executar

\`\`\`bash
python scripts/tutorial_editor.py \
  --source "/caminho/privado/gravacao.mp4" \
  --recipe tutorials/github_primeiro_repositorio.json \
  --output "outputs/github_tutorial.mp4"
\`\`\`

O arquivo de referência gravado em 08/11/2026 tem **512×1108, ~172s**, e a receita foi calibrada para ele. A receita é **um exemplo**, não contém o vídeo nem os dados pessoais. Para usar outra gravação, ajuste os intervalos, a resolução e as máscaras.

### Segurança/controle de qualidade

- \`privacy_masks\`: blocos opacos sobre coordenadas x, y, width, height no vídeo original, delimitados por \`start\` e \`end\`.
- Se uma máscara interceptar parcialmente um take, o render **falha** até o take ser integralmente coberto ou recortado.
- O áudio original da gravação não é reutilizado. Não há redes, API externa, chaves, serviço pago nem envio de arquivo.
- O vídeo final precisa de **revisão visual manual** para proteger outros nomes, notificações, e-mails, fotos ou tokens: a receita NÃO faz detecção automática de PII.
- Nenhuma publicação automática em TikTok, YouTube ou outras plataformas.
- \`python -m unittest discover -s tests -v\` executa os testes da integração.

### Próximo passo de automação

Para uma automação 100% privada, armazene as gravações numa pasta local monitorada do runner self-hosted e acione esse editor com a receita correspondente. GitHub-hosted Actions **não recebem automaticamente** os MP4 anexados no ChatGPT; não use URLs públicas com dados particulares. Um conector de armazenamento privado é opção explícita, não pré-requisito.

Vídeos de referência de terceiros servem **apenas como referência de ritmo/estética**; não são copiados nem se reutiliza a música deles.
