---
name: moneyprint-motion-qa
description: Validação de vídeos e animações renderizados no MoneyPrint
---

# MoneyPrint Motion QA — P1/P2

## Critérios de aceite
- Compare a duração real ao storyboard, permitindo apenas o arredondamento por frame e sobreposições explicitamente configuradas.
- `ffprobe` deve encontrar stream de vídeo, resolução correta e stream de áudio quando houver narração.
- Extraia PNG de início, transição, meio e fim; não aceite frames inteiramente pretos/brancos involuntários, texto fora da margem ou barras alterando a proporção.
- Gancho deve tocar em velocidade original e fazer corte seco quando `transition: cut`.
- Música e takes só podem vir de fontes aprovadas; mantenha créditos em JSON/TXT.
- SRT deve permanecer alinhado após edição; `auto_cut` exige regeneração de timings antes de publicação.
- Não mude OAuth, secrets, rotas existentes ou permissões; opções experimentais devem ser explícitas.
- Nunca marque QA como verde sem evidência da execução real.

## Modos testáveis
```bash
python -m unittest discover -s tests -v
python -m scripts.qa_video_stack --output qa-video-stack --transition cut
python -m scripts.qa_video_stack --output qa-video-stack --transition fade
```

Não publique automaticamente no TikTok/YouTube.
