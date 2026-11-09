---
name: moneyprint-reference-analyst
description: Análise local de ritmo, cortes e enquadramentos sem copiar imagens da referência
---
# MoneyPrint Reference Analyst — P1

1. Trabalhe somente com vídeo que o usuário tenha direito de analisar. Não reutilize imagens da referência no vídeo final sem autorização.
2. Rode \`python -m scripts.reference_analyzer --input assets/referencia.mp4 --output outputs/referencia.json\` no executor local/Actions.
3. Reporte duração, FPS, resolução, timestamps de cortes, número de planos e cadência observada.
4. Distinga rigorosamente **medição factual** (cortes por FFmpeg) de **heurística fraca** (região de detalhes por OpenCV). Nunca apresente heurística como detecção confiável de pessoas, objetos ou intenção estética.
5. Recomende ritmo, transições e enquadramento sem restringir a criatividade nem inventar imagens.
6. Armazene apenas relatório e metadados no Studio; referência original fica em armazenamento privado/local.
7. Core R$ 0 e self-hosted. Não introduza APIs comerciais.
