# Studio V3 — pipeline cinematográfico P3–P5

## Entregas reais

- **P3 — render canônico:** `scripts/studio_render.py` usa o JSON V3 como fonte de duração e ordem. Valida lacunas/sobreposições, mídias aprovadas e saída real de frames via FFprobe; suporta 16:9, 9:16 e 1:1. As operações antigas `github_cinematic` permanecem intactas.
- **P3 — voz e marcação:** Piper pt-BR local, áudio por cena, ajuste limitado de velocidade (não corta fala silenciosamente), arquivo de palavras com estimativas identificadas. `--align-words` é opcional e usa reconhecimento de fala local; estimativa não é alinhamento forçado de fonemas.
- **P4 — direção visual:** `scripts/studio_visuals.py` cria fluxogramas contextuais de ERP, CRM, atendimento, projetos e documentos; layouts de comparação, cards, painéis browser, abertura e conclusão. Capturas reais dos repositórios GitHub via Playwright (opt-in) aparecem em molduras; não recria telas como supostas capturas factuais. Movimento de câmera/zoom suave no FFmpeg, cortes secos.
- **P4 — edição mobile:** interface Studio já permite edição, ordem e duração das cenas, biblioteca aprovada, undo/redo e salvamento explícito com CSRF e controle de revisão. O botão **Renderizar MP4** envia a versão salva ao GitHub Actions sem autopublicar.
- **P5 — QA técnico:** testes Python e Node, validação de duração, codecs, áudio, frames, resolução, origem de mídia, limites e contrato de saída. O relatório não certifica estética. A revisão visual ainda é humana.

## Produção de cinco minutos

Projeto exemplo: `projects/5-sistemas-empresas-github-v3.json`, 300 segundos, 30 FPS e 9000 frames.

```bash
python -m scripts.studio_render --input projects/5-sistemas-empresas-github-v3.json \
 --root . --output outputs/5-sistemas --voice piper \
 --voice-model /caminho/para/pt_BR-faber-medium.onnx --capture-github
```

O arquivo de voz pode ser adquirido via `download_piper`, com SHA256 validado. O workflow `.github/workflows/studio-render.yml` instala os componentes livres e disponibiliza `studio_final.mp4`, `palavras.json`, `creditos.json` e `diagnostico.json` em artifact.

## Painel

1. Entre na sessão existente do MoneyPrint.
2. Abra **Cenas**, crie ou selecione projeto.
3. Edite roteiro, mídia aprovada, ordem/duração, salve explicitamente a revisão.
4. Clique **Renderizar MP4**. O Worker publica exclusivamente o JSON salvo em `studio-requests/studio-<id>-r<revision>.json` e despacha `studio-render.yml` com token GitHub já conectado.
5. Consulte **Execuções** e revise o artifact antes de qualquer publicação.

Rerenders da mesma revisão atualizam o arquivo GitHub com SHA para evitar erro 422. Nenhuma credencial vai para o JSON.

## Limites e próximos refinamentos

- Prévia do painel representa storyboard e não reprodução frame-a-frame do MP4.
- Ainda não há edição de keyframes individuais em camadas nem arrastar trilhas independentes de áudio/vídeo diretamente na timeline.
- B-roll precisa estar aprovado, disponível em `assets/` e registrado com licença; não há download indiscriminado de clipes virais.
- Marcação lexical é estimada por padrão, não uma promessa de sincronismo exato por palavra.
- Serviço pago é opcional e não é necessário ao render. Hospedagem e minutos de GitHub Actions seguem limites do provedor; o runner pode ser self-hosted.

## Regras permanentes

Não modificar OAuth, autenticação, secrets, workers de produção ou versões legadas sem validação. Não aceitar mídia com caminho inseguro, licença ausente ou alegação de notícia sem fonte. Não bloquear renderização por juízo estético, mas manter revisão visual antes de publicar.
