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

## Diversidade visual e entrada de personagens — regra editorial

9. **Não repetir IDs de motion entre cenas** por padrão. Para uma única produção, selecionar um motion original diferente por take; recorrer a repetições somente quando forem indispensáveis à continuidade narrativa e justificar cada exceção no storyboard. Nunca repetir por conveniência ou para preencher tempo. Consultar catálogo e exemplos reais em vez de reconstruir um motion com formas próprias.
10. Quando houver personagem animado que serve de explicador (chat-bubbles, box-bot, etc.), introduzi-lo **no início do bloco explicativo**, com fala ou pergunta desde os primeiros frames. Não guardar o personagem apenas para o último take ou para os segundos finais.
11. Verificar no QA a lista de IDs, a posição temporal do personagem, os frames iniciais e a relação entre narração e animação. A prévia deve ser inspecionada visualmente antes de aprovar o vídeo.
