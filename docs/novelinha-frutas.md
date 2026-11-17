# Frutalândia — episódio 1

## Fluxo real de renderização (PR #4, sem publicação)

Fluxo independente do MoneyPrinterTurbo convencional, com núcleo R$ 0, fonte aberta
e saída somente para revisão.

1. `stories/frutalandia/audio-do-amanha-ep01.json`: roteiro canônico, 4 frutas, 6 cenas e 48 segundos.
2. `scripts/novelinha_frutas.py`: gera bible de continuidade, plano de cenas compatível com OpenMontage e falas para VoiceStudio.
3. `scripts/frutalandia_kaggle_bundle.py`: empacota somente código + storyboard em um notebook Kaggle **privado**. Nenhum secret é empacotado.
4. `.github/workflows/frutalandia-gpu.yml`: valida testes, identifica o usuário a partir de `KAGGLE_API_TOKEN`, consulta cota quando disponível, envia kernel com T4x2, monitora e recupera MP4.
5. `scripts/frutalandia_blender.py`: produz **animação de objetos 3D reais** com malhas de frutas, corpos, expressões, camera, ambientes e iluminação Blender Cycles CUDA; CPU é fallback.
6. `scripts/frutalandia_episode_runner.py`: sintetiza voz em português (Piper local), oferece VoiceStudio se um backend local **real** estiver ativo, gera trilha original, hardcode de legendas, FFmpeg e valida streams via ffprobe.
7. Artifacts do GitHub: `frutalandia-ep01.mp4`, `capa.png`, `captions.srt`, `manifest.json`.

## O que é — e o que não é

- É animação tridimensional procedural construída no Blender (personagens persistentes e animados, cortes de câmera, geometria).
- O compositor de produção realmente executado é FFmpeg. **OpenMontage gera um plano compatível, mas seu runtime/HyperFrames não é executado no job Kaggle.**
- O provedor padrão de voz é Piper, com timbres variados para cada fruta. **VoiceStudio é opcional**, somente se um servidor local funcional e quatro perfis cadastrados estiverem disponíveis.
- **Não executa Wan 2.1**. A abordagem procedural foi escolhida para garantir identidade visual e caber na cota sem download de pesos enormes. Um backend Wan pode ser acrescentado como alternativa explícita.
- A renderização nativa usa 360×640 a 12 FPS para caber no core gratuito, convertida para 720×1280/24 FPS. Isso não representa resolução nativa 720p, nem animação cinematográfica gerada por difusão.
- Custo de API: R$0. A GPU do Kaggle depende de quota e elegibilidade, sem garantia de disponibilidade.
- Não publica automaticamente no TikTok ou YouTube; não altera a main sem testes.

## Execução

O workflow é `Frutalândia 3D — render Kaggle GPU` e foi lançado pela alteração de
`triggers/produce-frutalandia.txt` na branch da PR #4.

Uma vez o workflow presente na branch default, ele também pode ser iniciado manualmente pela aba Actions. O secret `KAGGLE_API_TOKEN` já configurado é usado pelo GitHub runner, sem imprimir o valor.

- [Workflow de render](https://github.com/nutricionistaalmeidavh-spec/moneyPrintTest/actions/workflows/frutalandia-gpu.yml)
- [PR #4](https://github.com/nutricionistaalmeidavh-spec/moneyPrintTest/pull/4)

Gates de aceitação: os testes devem passar; a execução Kaggle precisa concluir sem falhas; saída MP4 deve existir e ter 720×1280, 48 ±1s, codec H.264 e faixa de áudio AAC. O manifest precisa afirmar `status=rendered`; nenhum status fictício é aceito.

## QA de geometria no Actions

O workflow `Frutalândia — QA de geometria 3D real` instala Blender no runner CPU e renderiza um frame usando `FRUTALANDIA_SMOKE=1`. Isso valida geometria, cenas e compatibilidade da versão do Blender, mas **não** substitui o E2E de 48 segundos.

## Limitações conhecidas

- A aparência é inspirada na descrição dos personagens, não em arquivos de imagem anteriores — não há referência PNG original versionada no repositório.
- Os movimentos de boca são estilizados; não incluem lip-sync fonético avançado.
- Profundidade de campo e 3D polido dependem das amostras de Cycles e da GPU disponível.
- O render do Kaggle pode expirar, ficar na fila ou falhar por configuração/limites do servidor; nesse caso o workflow falha explicitamente e preserva logs no próprio Kaggle.
- O VoiceStudio, quando ativado, não clona vozes humanas sem autorização.

## Execução local opcional

Se Blender e FFmpeg estiverem instalados e houver modelos Piper disponíveis:

```bash
python scripts/frutalandia_episode_runner.py \
  --story stories/frutalandia/audio-do-amanha-ep01.json --output outputs/frutalandia
```

Para VoiceStudio real, configure `VOICE_STUDIO_URL=http://127.0.0.1:3900`
**no mesmo executor** e cadastre os perfis moranguete, uva, mae-pera e pai-caju.
No Kaggle essa URL normalmente não existe; por isso Piper é o modo padrão. Nenhum serviço pago é habilitado.
