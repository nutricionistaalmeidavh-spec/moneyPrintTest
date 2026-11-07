# Frutalândia — Image-to-Video com referência fixa (R$ 0)

Este fluxo **não usa os bonecos de esferas do Blender como fonte**. A imagem do elenco criada no chat está versionada no GitHub em `assets/frutalandia/elenco-master.webp` (1672 × 941). A versão original em PNG está preservada no pacote de referências entregue no chat. As seis primeiras imagens verticais são recortadas dessa arte original e cada contador é corrigido conforme o roteiro.

## Onde executar

1. **GitHub Actions (preparação gratuita)** — [Frutalândia I2V](../.github/workflows/frutalandia-i2v.yml), `mode=prepare`: valida integridade, os quatro personagens e seis cenas, cria `first-frame-s01..s06.png` e publica artifact de referências. **Não baixa nem executa modelo de IA** no runner hospedado: ele não tem GPU NVIDIA.
2. **Google Colab gratuito (opcional)** — [Notebook I2V](../notebooks/frutalandia-i2v-referencia.ipynb). Selecionar ambiente com GPU NVIDIA, executar as células. Usa a imagem versionada sem reupload e gera **somente 2 segundos** de uma cena inicialmente.
3. **Self-hosted NVIDIA (principal)** — adicionar um GitHub Actions runner Linux x64 com label `frutalandia-gpu` e CUDA disponível, instalar FFmpeg/Python e acionar `workflow_dispatch mode=preview scene=s01`. A Action exige GPU real de aproximadamente 10 GB VRAM ou mais para esse perfil; a disponibilidade e desempenho variam. O runner é autogerenciado, sem serviço pago.
4. **Produção de 8s** — selecionar `mode=scene` com `approve_full=true` só depois de analisar a prévia. O programa não considera imagem inicial ou slide estático como vídeo concluído.

## Pipeline

- **Fonte canônica**: `assets/frutalandia/reference-manifest.json` — SHA-256, recortes e contadores 000/007/999+/038. Os números do pôster não prevalecem sobre o storyboard. Imagem mestre em `assets/frutalandia/elenco-master.webp`; thumb em `assets/frutalandia/elenco-reference.webp`.
- **Storyboard**: `stories/frutalandia/contador-do-butico-ep01.json`, seis cenas de 8 segundos. Model prompts: comédia nordestina, ambiente de feira livre, atuação expressiva e preservação de características.
- **Modelo I2V**: `LTXImageToVideoPipeline` com `Lightricks/LTX-Video-0.9.5` via Hugging Face Diffusers, pesos abertos baixados **somente** na primeira execução autorizada com GPU. Consulte a licença do checkpoint para utilização comercial. Backend sem API paga.
- **Exportação**: FFmpeg/H.264 e FFprobe validam frames, duração e dimensão; nada é aprovado apenas porque os testes unitários passaram. A prévia é sem voz, e o código da versão final utiliza Piper local para narração.
- **Gates**: não gerar os 48 segundos automaticamente, não fazer merge na main, não publicar em TikTok/YouTube e não alterar Secrets.

## Limitações reais

- Vídeo por difusão **pode alterar aparência de personagens**, mesmo condicionado pela primeira imagem. Consistência absoluta ou lip sync perfeito não são garantidos; o episódio completo depende de revisão visual da prévia.
- O primeiro frame atual vem do retrato de estúdio do pôster. **A feira nordestina é descrita no prompt**, mas não existe como imagem estática na referência. Um próximo aprimoramento pode introduzir primeiras imagens específicas de cada cenário, mantendo a identidade do elenco.
- A imagem de Uva no pôster parece masculina, enquanto o roteiro anterior descreve Uva no feminino. Esse conflito de direção e voz precisa de decisão editorial antes da produção final; não foi corrigido silenciosamente.
- Colab gratuito pode não disponibilizar GPU ou encerrar a sessão; a conta pode ter limites. Um runner GitHub hospedado com CPU **não é** substituto de uma GPU para o modelo.
- Baixar checkpoints pode exigir dezenas de GB de espaço e internet. Não afirme qualidade cinematográfica com base em QA sintático; inspecione o MP4 real.

## Comandos

```bash
# Preparar as seis primeiras imagens (CPU, Pillow)
python -m scripts.frutalandia_i2v prepare --out outputs/frutalandia-i2v

# Prévia REAL de 2s (GPU NVIDIA com dependências Diffusers e FFmpeg)
python -m scripts.frutalandia_i2v preview --scene s01 --out outputs/frutalandia-i2v

# Oito segundos, após aprovação
python -m scripts.frutalandia_i2v render-scene --scene s01 --approve-full --out outputs/frutalandia-i2v
```

Apenas quando as seis cenas de oito segundos estiverem validadas com MP4 verdadeiro é possível montar o episódio completo; nenhuma ferramenta gera automaticamente conteúdos falsos para preencher falhas.
