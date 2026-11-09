# MoneyPrintTest — vídeos automáticos da ArtiSys

Controlador de vídeos para **GitHub Actions**, sem seu PC ligado e sem APIs pagas obrigatórias. Usa o motor original [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo), versão `mpt==1.3.9`, e componentes locais.

## Stack de vídeos P0–P2 — cortes, motion e animações 3D (opt-in)

O modo `github_cinematic` mantém o editor de slides animados da `main` e aceita
um objeto `motion` opcional: corte seco, gancho local sem câmera lenta,
abertura espacial em 30 FPS (FFmpeg/Pillow ou Three.js), indexação com
PySceneDetect, Auto-Editor, projetos HyperFrames/OpenScreen e clipes Motion Canvas.
Nenhuma API ou serviço pago é necessário; adaptadores extras são instalados
somente quando selecionados. O vídeo resultante e os relatórios ficam nos
**Artifacts**, sem publicação automática.

- [Manual P0–P2, requisitos e execução](docs/video-stack-p0-p2.md)
- [Pedido de exemplo com roteiro completo](docs/examples/artisys-oito-repositorios-motion-p0-p2.json)
- Workflow de QA: **QA P0-P2 — cortes, áudio e motion local**

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

### Formato editorial V2: slides animados como base

Para vídeos com repositórios, use `"visual_mode": "github_cinematic"`.
O renderizador `scripts/motion_pipeline.py` faz a produção nova sem reutilizar
o MOV antigo. O **slide animado é a linguagem principal**, não uma gravação
de tela:

1. Abertura limpa e argumento do projeto.
2. Fluxograma com três etapas reveladas progressivamente.
3. Screenshots originais do README em mockup de navegador com movimento de câmera.
4. Vídeos contextuais e GIFs oficiais em inserções **curtas** dentro do mockup,
   quando houver material real disponível.
5. Aplicação prática e passagem direta ao próximo repositório.

**Sem flashes brancos nem crossfade longo**: o editor usa cortes secos entre
quadros escuros com suave movimento de câmera gerado no FFmpeg. Playwright
captura imagens nítidas da página inicial e do README em posições relevantes,
sem gravar scroll travado. Nada do vídeo de referência é reaproveitado como imagem.

Ferramentas gratuitas: Chromium/Playwright, FFmpeg, Pillow, Piper,
fontes Lato/DejaVu e Wikimedia Commons. GIFs e screenshots só são considerados
quando procedem do projeto oficial; mídia de terceiros recebe créditos e
licenças quando necessário. Clipes de vídeo fornecidos pelo criador também
podem ser usados. **Não há trava editorial para vídeos.** A única regra
editorial rígida de conteúdo é **não inventar notícia**: headlines só entram
com fonte, data e URL verificáveis, ou são omitidas.

O sistema salva MP4 1920×1080, arquivo de roteiro, SRT estimado editável,
`storyboard_animado.json`, créditos e proveniência. O modo
tradicional `github` e os demais modos MoneyPrinterTurbo continuam disponíveis.
Para o exemplo de oito projetos, consulte
`docs/examples/artisys-oito-repositorios-cinematic.json`.

A execução roda no GitHub Actions (ou runner próprio) e disponibiliza artifact
para revisão, sem publicar automaticamente em redes sociais e sem dependência
de serviços pagos. O Ollama permanece disponível nos modos legados, mas a
edição visual V2 é determinística para garantir consistência de apresentação.

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

### Edição cinematográfica: vídeo, GIF, motion e notícia verificável

O modo `github_cinematic` é **opt-in** e preserva os modos existentes.
Combina navegação real no GitHub com movimentos editoriais de câmera, fontes
**Inter** e vídeos contextualizados, em Full HD. O código mantém o áudio
original da montagem e não impõe um bloqueio geral a arquivos de vídeo.

- **Mídia:** vídeo/GIF enviado pelo usuário em `assets/` (`mp4`, `mov`,
  `webm`, `gif`) > GIF oficial encontrado no README > b-roll contextual
  Wikimedia Commons quando houver. Várias fontes podem aparecer no mesmo
  capítulo, intercaladas com a navegação real. Não há necessidade de API paga.
- **Motions:** animações de entrada/saída, destaque de repositório, movimentos
  em capturas e lower-thirds discretos, sem cards gigantes.
- **Notícias:** `include_verified_news: true` é opcional. Apenas manchetes
  reais encontradas em RSS, com veículo e data, são renderizadas. Se não
  houver notícia confirmável, **nenhuma é inventada ou substituída por uma
  manchete sintética**. Todo registro utilizado fica em
  `noticias_verificadas.json`.
- **Fontes:** Inter (instalada no workflow, licença aberta), com fallback
  de sistema. Não é necessário incluir arquivos de fontes no projeto.

Para adicionar seus próprios takes:

```json
{
  "topic": "8 projetos open source",
  "visual_mode": "github_cinematic",
  "duration_seconds": 300,
  "aspect": "16:9",
  "repo_urls": [
    "https://github.com/appwrite/appwrite",
    "https://github.com/payloadcms/payload"
  ],
  "sections": [
    {
      "repo_url": "https://github.com/appwrite/appwrite",
      "title": "Appwrite",
      "narration": "Appwrite entrega uma base de autenticação e APIs para aplicativos.",
      "broll_query": "software developer working laptop"
    },
    {
      "repo_url": "https://github.com/payloadcms/payload",
      "title": "Payload CMS",
      "narration": "Payload oferece conteúdo estruturado, painel e APIs extensíveis.",
      "broll_query": "person editing website content"
    }
  ],
  "media_clips": [
    {"repo_index": 1, "path": "assets/appwrite-demo.mp4"},
    {"repo_index": 2, "path": "assets/payload-presentation.gif"}
  ],
  "include_verified_news": false
}
```

No exemplo, os arquivos são opcionais: se não existirem, o pipeline avisa
e continua com captura de navegador/demos ou b-roll. Para vídeos de maior
duração, escreva um roteiro realmente compatível com a duração, preferindo
seções de narração mais completas. O vídeo final segue a duração da voz.

É possível remasterizar um arquivo existente sem alterar a narração:

```sh
python scripts/cinematic_post.py \
  --source video_original.mp4 --output video_remasterizado.mp4 \
  --repos-json repos.json
```

O QA `QA cinematografico - motion + b-roll + navegador` visita os oito
repositórios e publica clipes de navegador e material contextual para
inspeção. **Não publica automaticamente nas redes.**

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
