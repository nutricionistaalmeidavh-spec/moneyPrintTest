# Remotion no MoneyPrint Studio (opt-in)

O MoneyPrint continua com **core R$ 0, self-hosted e open source**: FFmpeg/Python/Piper.
O motor Remotion é um adaptador **opcional**, instalado somente na execução escolhida.
Remotion é **source-available, licença proprietária**, não OSI open source.
Verifique [licença e elegibilidade](https://www.remotion.dev/docs/license/pricing).
Na data da implementação, a licença gratuita é disponibilizada para indivíduos e
equipes de até 3 pessoas, inclusive automação comercial, sujeita aos termos.

## Como usar no painel

1. Abra **MoneyPrint Studio → Cenas**; ao criar um projeto selecione **Motor de renderização → Remotion (opcional)**.
2. No projeto existente, selecione **Remotion** e clique em **Salvar revisão**.
3. Clique em **Renderizar MP4 no Actions**. O backend despacha `studio-remotion.yml`
   quando `render_engine: remotion` está salvo. A seleção padrão permanece
   `ffmpeg`; os projetos antigos continuam inalterados.
4. Encontre MP4, `remotion_props.json`, `creditos.json`, `palavras.json`
   e `diagnostico.json` nos Artifacts. **Nada é publicado automaticamente.**

O estilo de edição e o motor são opções independentes: `visual_style` pode ser
`classic` ou `light_motion`. **Talkcraft** continua separado, somente educacional
não comercial, e não é importado pela composição independente.

## Local / runner self-hosted

```sh
cd motion/remotion
npm install --no-audit --no-fund
npx remotion browser ensure
cd ../..
python -m unittest tests.test_remotion_render -v
python -m scripts.remotion_render --input projects/remotion-smoke-v3.json \
  --root . --output outputs/remotion-smoke --voice none
```

Para narração real, instale Piper/FFmpeg, passe `--voice piper --voice-model /caminho/voz.onnx`
e, se desejar capturas reais, `--capture-github` (Playwright). Cada cena segue
`start_frame` e `duration_frames` do Studio V3; a composição React cria
movimento/zoom e pode incorporar fotos e vídeo existentes em `assets/`
com licença, origem e aprovação. GIF, MOV e MKV são transcodificados pelo FFmpeg.
Falta de mídia aprovada ou do Remotion instalado **interrompe com erro explícito**:
não existe substituição silenciosa pelo motor legado.

**Cuidados:** o pré-visualizador existente mostra storyboard, não quadros finais
do Remotion; a primeira validação deve incluir artifact MP4. O adaptador usa
marcação lexical estimada, não promessa de sincronização forçada. GitHub Actions
está sujeito a limites/cobranças do provedor; é possível executar em runner próprio.
Não modifica OAuth, tokens, Worker publicado ou instalações já existentes.
