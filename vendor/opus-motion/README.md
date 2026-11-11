# Opus Motion Library — componentes originais selecionados

Origem: https://github.com/GovinduSasanka/opus-motion-library  
Revisão fixa do upstream: `8f1b78a25d0cf310c9bf904d434285046c4ed25a`  
Licença das animações: MIT (ver `LICENSE` e `THIRD_PARTY_NOTICES.md`).

## Fontes originais baixadas e mantidas neste repositório

| Intervalo no piloto | Motion original | Código mantido |
|---|---|---|
| 00:00–00:03.30 | `breaking-news-takeover` | `src/motions/hud/breaking-news-takeover.tsx` |
| 00:03.30–00:09.05 | `cause-effect-chain` | `src/motions/data/cause-effect-chain.tsx` |
| 00:09.05–00:12.00 | `board-camera` | `src/motions/camera/board-camera.tsx` |

As fontes TSX originais foram preservadas **sem modificações** para edição e substituição futura.

## Execução sem custos e sem dependências proprietárias

O motor padrão executa adaptações da coreografia original usando apenas Pillow + FFmpeg em `scripts/opus_motion_adapter.py`. **Não utiliza o Remotion em nenhuma etapa da renderização padrão.** A composição final é montada por `scripts/pilot24_editor.py --opus-motions`.

O código do Opus Motion é MIT, mas **Remotion não tem licença OSI open source e exige licenças conforme o contexto empresarial**. Assim, qualquer opção futura que instale/remonte Remotion deve ser opt-in explícito, nunca dependência do core de custo zero.

As versões Python são uma **adaptação funcional MIT da gramática de movimento**, e não uma renderização pixel a pixel das composições originais React. A revisão deve comparar o resultado visual com as referências; o código original fica no repo para evoluir essa fidelidade.

## Política editorial

- `breaking-news-takeover`: adaptado como um alerta editorial **não factual**, sem alegar notícia, cobertura ao vivo ou evento não verificado.
- `cause-effect-chain`: retrabalho em etapas; sem números financeiros inventados.
- `board-camera`: câmera fluida percorrendo Vendas, Estoque e Financeiro.
- 12–24 segundos: preservar as capturas reais do ERPNext; não usar animação que encubra a interface.
- `budget-envelope-split`: não usado neste vídeo porque seria necessário inventar valores.
- `chat-bubbles`: não usado porque a narração não menciona mensagens ou atendimento.
- `counting-objects`: não usado porque a estética infantil é inadequada para este assunto.

### Executar localmente

`python -m scripts.pilot24_editor --project projects/5-sistemas-talkcraft-educacional.json --voice-model /path/para/pt_BR-faber-medium.onnx --out outputs/pilot24 --opus-motions`

Requer Python + Pillow, FFmpeg, Piper e Playwright para capturar a aplicação pública. Não requer tokens de API. A rotina GitHub Actions `.github/workflows/pilot24.yml` produz automaticamente a prévia, narração e quadros QA.

**Nenhum vídeo é publicado automaticamente.** A aplicação verdadeira continua sendo capturada de fonte pública e a origem permanece registrada apenas nos diagnósticos.
