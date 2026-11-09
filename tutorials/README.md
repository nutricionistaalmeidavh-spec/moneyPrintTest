# MoneyPrint — tutoriais de tela em vídeo curto

Modo complementar e isolado ao MoneyPrinterTurbo: FFmpeg + Pillow e JSON local. A gravação original NÃO deve ser enviada a um repositório público. Workflows, tokens e segredos atuais permanecem intactos.

## Exemplo GitHub

Receita: tutorials/github_primeiro_repositorio.json

- Gancho: moto em velocidade original por 0,7 segundo, seguida de corte seco sem crossfade.
- Universo: GIF animado de 2,3 segundos; a abertura completa soma 3 segundos.
- Conteúdo: nove takes acelerados da gravação com interface limpa, **sem contador superior e sem legendas de ação inferiores**.
- Segurança: máscaras sólidas irreversíveis antes do redimensionamento. Revisão visual humana obrigatória, pois não há identificação automática de outros dados pessoais.
- Trilha gerada localmente, sem áudio original da moto ou da gravação.

## Rodar sem serviços pagos

Dependências: Python 3.11+, FFmpeg, ffprobe, Pillow e fontes DejaVu. Tenha uma gravação local, clipe de moto autorizado e um GIF de universo licenciado ou original.

    python scripts/tutorial_editor.py \
      --source "/pasta-privada/gravacao-github.mp4" \
      --hook-source "/pasta-privada/gancho-moto.mp4" \
      --universe-gif "/pasta-privada/universo.gif" \
      --recipe tutorials/github_primeiro_repositorio.json \
      --output "/pasta-privada/tutorial-final.mp4"

Core R$ 0, self-hosted e open source, sem assinatura ou API paga. O GitHub Actions hospedado está sujeito a limites e custos próprios da conta; não é dependência necessária deste editor.

A gravação de referência compartilhada pode conter conteúdo de terceiro; antes de publicar, confirme o direito de usar o trecho da moto. Não existe publicação automática.

## Testes

    python -m unittest discover -s tests -v

As verificações incluem duração natural do gancho, remoção de camadas com legendas, dimensões da fonte e cobertura de máscaras. A receita deve ser recalibrada ao mudar de gravação.
