# Frutalândia — novelinhas com OpenMontage, VoiceStudio e Kaggle

## Escopo atual (primeira etapa, **não** é renderização E2E)

Este workflow mantém o fluxo MoneyPrinterTurbo existente isolado.
A nova Action **Novelinha de frutas — planejamento e preflight GPU** faz:

1. Carrega um episódio JSON versionado e valida duração, personagens e identidade visual.
2. Gera `openmontage-brief.json` com cenas, ações, figurino, enquadramentos e referências visuais.
3. Gera `voicestudio-lines.json` com cada fala, personagem e identificador de perfil de voz.
4. Gera `character-bible.json` com identidade estável por episódio.
5. Opcionalmente, testa a presença de GPU CUDA em um **notebook privado Kaggle**, sem renderização nem publicação.

**Não gera MP4 nem afirma ter usado OpenMontage ou VoiceStudio para sintetizar a obra.**
O brief é o insumo para a pipeline de animação `character-animation` do OpenMontage.
O adaptador HTTP do VoiceStudio é funcional com backend local e perfis previamente cadastrados, mas **não há backend VoiceStudio inicializado automaticamente no Actions/Kaggle nesta etapa**.

## Fontes (versões de upstream a fixar na etapa de render)

- OpenMontage: https://github.com/calesthio/OpenMontage — `character-animation` com HyperFrames, atuação de personagem, validação de cenas e renderização
- VoiceStudio: https://github.com/debpalash/VoiceStudio — API local `/v1/audio/voices` e `/v1/audio/speech`
- Kaggle: https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels.md — `kernels push/status/output`

Os dois projetos usam **AGPL-3.0**; observar também as licenças dos modelos, pesos e mídias externos.

## Episódio inicial

`stories/frutalandia/audio-do-amanha-ep01.json`

Enredo "O Áudio de Amanhã", com Moranguete, Uva, Mãe Pera e Pai Caju. Drama cômico CGI 3D original, iluminação quente, figurino fixo, seis cenas, 48 s, formato 9:16. Sem overlays de WhatsApp.

## Executar planejamento

```bash
python -m unittest discover -s tests -v
python scripts/novelinha_frutas.py stories/frutalandia/audio-do-amanha-ep01.json \
  --output outputs/frutalandia-plan
```

Os arquivos são enviados como GitHub Artifacts quando a Action é disparada manualmente. Não há cron nem postagem automática.

## Testar GPU Kaggle pela Action

A credencial esperada já é `KAGGLE_API_TOKEN` nos GitHub Secrets; ela nunca é impressa.

No menu Actions → "Novelinha de frutas — planejamento e preflight GPU" → Run workflow:

- `story_path`: caminho versionado do episódio
- `gpu_preflight`: ativar apenas quando quiser consumir cota do Kaggle
- `kaggle_username`: usuário **público** do Kaggle, necessário para o ID do notebook

A Action cria notebook privado, pede GPU T4 e baixa diagnóstico `gpu_preflight.json`. **Este teste não renderiza vídeo.** Precisa que a conta tenha permissão de GPU e internet não é necessária para a prova.

## VoiceStudio local

Para testar o adaptador, inicie o VoiceStudio em loopback `127.0.0.1:3900` pelo servidor/Docker oficial e cadastre quatro perfis de voz cujos IDs correspondam ao JSON (`moranguete`, `uva`, `mae-pera`, `pai-caju`). Não faça clonagem de voz humana sem autorização.

```bash
python scripts/novelinha_frutas.py stories/frutalandia/audio-do-amanha-ep01.json \
  --output outputs/frutalandia-plan \
  --voicestudio-url http://127.0.0.1:3900
```

Caso o servidor/perfil não exista, **falha explicitamente**; não entrega áudio falso. O arquivo WAV de cada fala sai em `outputs/frutalandia-plan/audio/`.

## Para concluir o episódio realmente animado (pendências)

- [ ] Referências visuais originais persistentes para cada fruta, sem mudar cabelo/roupa entre as cenas
- [ ] Executar um agente OpenMontage com `character-animation` e HyperFrames (ou provedor local de vídeo GPU explicitamente selecionado) para movimento de personagens, não imagens estáticas fingindo 3D
- [ ] Subir VoiceStudio de forma reproduzível no executor e provisionar vozes distintas pt-BR, integrando os WAVs à linha do tempo
- [ ] Testar o modelo de vídeo local na VRAM e cota reais do Kaggle; identificar quais cenas requerem modelo GPU em vez de rigs SVG
- [ ] Implementar runner de render remoto, recuperação de MP4 e gates (ffprobe, cenas, áudio, consistência, licença e versão)
- [ ] Fazer E2E do episódio 1 e só então habilitar modo de renderização, sem publicação automática

### Política de custos

Core: R$ 0 / open source / execução local ou nas cotas gratuitas elegíveis. Nenhum provedor comercial é habilitado automaticamente. Não modificar secrets existentes. Não executar o preflight GPU sem seleção explícita.

### Política de publicação

Sem postagem TikTok/YouTube automática e sem merge na main antes da validação dos testes de integração.
