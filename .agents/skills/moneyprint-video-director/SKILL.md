---
name: moneyprint-video-director
description: Criação de storyboards animados, ganchos e B-roll verificado para MoneyPrint
---

# MoneyPrint Video Director (P1)

1. Crie roteiro real com fontes; não invente notícias nem estatísticas.
2. Planeje vídeo como slides animados com fluxogramas, mockups, clips reais e GIFs do README original.
3. Priorize gancho de 0,5–3s com velocidade normal e corte seco. Não insira counters “1 de 2”, legendas de ação ou flashes brancos.
4. Mostre cenas coerentes com cada frase. Capturas devem ser das URLs reais; não simule interfaces como fatos.
5. Intercale B-roll licenciado sem depender de bancos pagos. Preserve créditos, URLs e licença.
6. Use títulos legíveis e margens seguras. Tipografia deve ser nítida em 1080p, sem zoom travado.
7. Teste formato 9:16 e 16:9, verificando duração, narração, cortes e legibilidade.
8. Core gratuito self-hosted com FFmpeg, Playwright, Piper, Pillow, PySceneDetect e Three.js. Serviços comerciais somente quando solicitados.

## JSON opt-in

```json
{
  "motion": {
    "hook_asset": "assets/hooks/aprovado.mp4",
    "hook_seconds": 1.8,
    "universe_seconds": 1.2,
    "universe_title": "OPEN SOURCE",
    "transition": "cut"
  }
}
```

Esse objeto é para `visual_mode: github_cinematic`. O arquivo local deve existir antes do envio ao GitHub.
