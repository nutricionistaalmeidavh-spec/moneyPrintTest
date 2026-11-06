# MoneyPrintTest — vídeos automáticos da ArtiSys

Controlador de vídeos para **GitHub Actions**, sem seu PC ligado e sem APIs pagas obrigatórias. Usa o motor original [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo), versão `mpt==1.3.9`, e componentes locais.

## Como pedir um vídeo pelo ChatGPT + GitHub

1. Crie **um novo** arquivo JSON em `requests/` na branch **main**. O ChatGPT com o GitHub conectado pode criar esse arquivo usando as ferramentas de escrita do repositório.
2. O commit dispara automaticamente o workflow **Gerar vídeo MoneyPrinterTurbo**. Não é necessário comando direto de `workflow_dispatch`.
3. O GitHub instala o MoneyPrinterTurbo, gera roteiro e palavras-chave com **Ollama local** quando não fornecidos, narração brasileira com **Piper offline** e legendas com **Whisper tiny local**.
4. Baixe o arquivo em **Actions → execução → Artifacts → moneyprint-...**. Ele contém MP4, roteiro e informações de execução. O material é para revisão, **não é publicado automaticamente** no TikTok/YouTube.

Pedido mínimo — basta o assunto:

```json
{
  "topic": "Como usar ferramentas open source para organizar uma obra",
  "duration_seconds": 35,
  "aspect": "9:16",
  "visual_mode": "auto"
}
```

Pedido com roteiro e termos definidos pelo ChatGPT (evita carregar LLM no runner):

```json
{
  "topic": "Ferramentas gratuitas para pequenas empresas",
  "script": "Você sabia que existem ferramentas gratuitas para organizar processos da empresa? Com software de código aberto, você pode usar os programas no próprio computador e adaptar as funções à sua rotina. Antes de escolher, teste recursos, segurança e facilidade de uso. Conheça as alternativas e selecione a mais adequada ao seu negócio.",
  "terms": ["small business office", "business management", "office teamwork", "laptop typing"],
  "duration_seconds": 40,
  "visual_mode": "auto"
}
```

### Buscar vídeos reais sem chave de API

O modo padrão é **Wikimedia Commons**, pela API pública, **sem cadastro ou chave**.

- `"visual_mode":"auto"`: pesquisa até três vídeos reais no Wikimedia Commons, converte os clipes para MP4 e usa na edição. Se não encontrar vídeos com licença aprovada, cria artes originais locais e informa o fallback.
- `"visual_mode":"stock"`: exige vídeos reais do Wikimedia Commons e falha explicitamente se não houver. **Não exige API key**.
- `"visual_mode":"local"`: sempre gera artes originais locais, sem acessar bancos de filmagem.
- `"visual_mode":"pexels"` ou `"visual_mode":"pixabay"`: são **opções manuais** para quem já possui chaves gratuitas. Não são exigidas nem ativadas automaticamente.

A pesquisa no Commons limita arquivos a **CC0** ou **CC BY** com metadados de licença, autor e página de origem. Os arquivos `creditos.txt` e `licencas_midia.json` são entregues junto ao vídeo; **publique os créditos na descrição** e confira o licenciamento antes de distribuir o MP4. Clipes são convertidos de WebM/OGV para MP4 usando FFmpeg. Nem todo tema tem vídeos adequados. Também podem existir direitos de imagem, marcas e outras restrições além do copyright.

Não há scraping do Pexels/Pixabay. A emissão de novas chaves do Pexels está suspensa desde 2026; Pixabay requer chave para sua API.

### Rodar novamente

Em **Actions → Gerar vídeo MoneyPrinterTurbo → Run workflow**, informe o caminho exato de um pedido existente como `requests/demo.json`. Alterar um arquivo antigo não reexecuta automaticamente; crie um novo JSON para novo vídeo.

### Arquitetura sem cobranças obrigatórias

- **Motor**: MoneyPrinterTurbo open source via PyPI, versão fixada.
- **Geração de roteiro quando necessário**: Ollama em Docker no runner, com `qwen2.5:1.5b`.
- **Voz brasileira**: Piper TTS local, modelo pt_BR-faber-medium (download sob demanda e conferência SHA256).
- **Legendas**: faster-whisper com modelo tiny.
- **Edição**: MoviePy/FFmpeg do MoneyPrinterTurbo.
- **Vídeos reais**: Wikimedia Commons sem chave por padrão, com créditos e licenças; Pexels/Pixabay são opcionais explícitos para quem já possui chave.
- **Execução**: GitHub Actions, com artefatos retidos por 7 dias.

GitHub Actions de repositórios públicos costuma ter execução gratuita em runners padrão, sujeita à política e aos limites do GitHub. A qualidade da locução, disponibilidade de bancos e tempo de renderização devem ser aferidos em execução real.

### Segurança, testes e limitações

O controlador valida campos, tamanhos, duração, nomes de arquivo e caminhos, usa listas de argumentos ao executar subprocessos e não ativa fornecedores pagos. Credenciais são criadas apenas em arquivos de configuração temporários, não versionados. Logs têm redação de chaves de mídia, mas não insira dados pessoais/sensíveis nos pedidos. Não há publicação automática.

Rodar testes sem dependências de produção:

```sh
python -m unittest discover -s tests -v
```

A duração em segundos orienta a geração do roteiro, e há validação de quantidade de palavras, mas o MP4 final segue a duração real da narração. O Ollama local pode falhar em produzir texto adequado (nesse caso a tarefa encerra com erro). Para máxima confiabilidade, peça ao ChatGPT para fornecer roteiro e termos no arquivo do pedido. Whisper tiny também pode errar legendas. O teste unitário não substitui o teste real de renderização no GitHub.
