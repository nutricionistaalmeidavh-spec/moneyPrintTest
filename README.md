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

### Novo vídeo cinematográfico: diretor de IA open source

Para criar **um vídeo novo**, diferente do vídeo de referência, use
`"visual_mode": "github_cinematic"` com `repo_urls` e `sections`.
Os oito repositórios são **gravados novamente, em páginas públicas reais**, pelo
Chromium/Playwright no GitHub Actions. O arquivo MOV de referência não é lido
nem incorporado na renderização.

A produção usa exclusivamente ferramentas locais gratuitas:

- **Ollama/Qwen local** como diretor editorial: decide ordem e duração dos takes,
  sugere buscas de b-roll contextual e só recebe IDs de mídias previamente
  recuperadas. Se estiver indisponível, uma edição determinística utiliza o
  mesmo material e o resultado registra esse fallback.
- **Chromium** para navegação e captura de páginas reais dos repositórios.
- **Wikimedia Commons** para vídeo contextual de usos cotidianos (ex.: restaurante,
  atendimento, escritório ou obras). Créditos são preservados.
- **README oficial** para GIFs e capturas de tela originais quando disponíveis.
- **Google News RSS** para possíveis manchetes com link, veículo e data
  conferidos. Sem fonte verificável, a notícia **não aparece** no vídeo;
  o modelo jamais inventa uma manchete.
- **Piper** para locução em português por seção, **FFmpeg/Pillow** para edição
  1920×1080, motion, cortes e tipografia leve Lato/Inter. Acompanha SRT
  editável com sincronização estimada, logs editoriais, fontes e licenças.

**Não há filtros editoriais para vídeos:** takes e fontes de vídeo podem variar,
inclusive clipes escolhidos pelo criador em `assets/` por
`media_clips`. Verifique direitos de uso dos vídeos de terceiros e os
créditos antes de publicar. O sistema **não inventa notícias** nem seleciona
arquivos inexistentes.

O nome do vídeo, os repositórios, o roteiro de cada seção e os termos de
contexto são controlados pelo JSON. Veja `docs/examples/artisys-oito-repositorios-cinematic.json`
para a edição inédita dos oito projetos.

A execução é pelo GitHub Actions e gera artifact para revisão, **sem
autopublicação**. Runners GitHub gratuitos para repositórios públicos seguem
os limites de uso do provedor; a mesma stack pode ser executada em
runner self-hosted próprio, sem APIs pagas.

### Gravar as páginas do GitHub como no computador (sem celular)

Use `"visual_mode": "github"` com 1 a 12 URLs de repositórios públicos.
O pipeline abre **Chromium com Playwright em desktop 1280×720**, visita cada
repositório, percorre a página e grava clipes reais. FFmpeg converte o WebM
para MP4; MoneyPrinterTurbo usa os clipes como material local e inclui a
narração do Piper e as legendas Whisper. Não exige chave, conta do GitHub
no navegador, celular, PC ligado nem serviço pago.

Exemplo de pedido para **8 repositórios / 5 minutos**, em `requests/8-repos.json`:

```json
{
  "topic": "8 projetos open source que ajudam a criar software",
  "duration_seconds": 300,
  "aspect": "16:9",
  "visual_mode": "github",
  "repo_urls": [
    "https://github.com/appwrite/appwrite",
    "https://github.com/payloadcms/payload",
    "https://github.com/FlowiseAI/Flowise",
    "https://github.com/docling-project/docling",
    "https://github.com/meilisearch/meilisearch",
    "https://github.com/keycloak/keycloak",
    "https://github.com/novuhq/novu",
    "https://github.com/Infisical/infisical"
  ],
  "script": "SUBSTITUA POR UM ROTEIRO REAL DE APROXIMADAMENTE 750 PALAVRAS",
  "terms": ["software development", "open source GitHub"]
}
```

**Importante:** o texto `script` do exemplo é apenas um marcador e **não**
deve ser usado para renderização. Para vídeos longos, forneça roteiro completo
com duração compatível. Se omitir `script`, o modelo Ollama local tentará
gerá-lo, mas poderá falhar na validação de comprimento; não é prometida
duração exata. A duração final acompanha a narração real. URLs permitidas
seguem exclusivamente o formato `https://github.com/owner/repo`;
não é permitido gravar sites arbitrários ou páginas privadas. O navegador
instala apenas neste modo, no GitHub Actions; os outros modos permanecem
com limite de 15–90 segundos.

O GitHub Actions publica os MP4 em **Artifacts**, retidos por 7 dias.
O uso de runners gratuitos está sujeito aos limites e à política de cobrança
da conta GitHub; nenhuma API comercial é dependência do projeto.

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
