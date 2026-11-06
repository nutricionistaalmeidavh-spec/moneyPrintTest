# Carrosséis de fotos reais para TikTok e Instagram

Sistema independente do gerador de vídeos, construído com Python/Pillow,
Pixabay gratuito (chave opcional), Wikimedia Commons e Ollama self-hosted.

## O que produz

- 2 a 10 arquivos JPEG de 1080 x 1350 (4:5) por padrão; 1080 x 1920 opcional, padrão seis;
- mesmo fundo fotográfico em todas as páginas (padrão) ou fundos distintos;
- títulos de alta legibilidade e textos reais sobre o fundo;
- preview.jpg para aprovar e carrossel.zip com todos os JPEGs;
- legenda.txt, creditos.txt, licencas_midia.json, roteiro.json;
- nunca publica automaticamente e nunca entrega a fotografia original isoladamente.

## Criar um pedido

Peça ao ChatGPT, com GitHub conectado, para criar um novo JSON em
carousel_requests/ na branch main. O commit dispara o workflow
"Gerar carrossel com fotos gratuitas". O artefato será exibido no
GitHub Actions, identificado por carrossel-NÚMERO_DA_EXECUÇÃO.

Pedido mínimo (conteúdo abaixo é JSON):

    {
      "topic": "4 sites para aprender programação",
      "slide_count": 6,
      "source": "auto",
      "photo_mode": "same",
      "style": "reference"
    }

O Ollama + Qwen local produz os textos das páginas quando não são
fornecidos. Para conteúdo com sites, preços ou outras afirmações, informe
os itens e fatos reais ou forneça slides explicitamente. O modelo não
verifica a atualidade de afirmações; a revisão editorial é obrigatória.

Pedido determinístico sem LLM (conteúdo abaixo é JSON):

    {
      "topic": "4 sites para melhorar na programação",
      "source": "auto",
      "photo_terms": ["modern desk setup", "minimalist computer desk"],
      "slides": [
        {"title": "4 sites que ajudam na programação", "body": "Salva este guia."},
        {"title": "Roadmap.sh", "body": "Trilhas visuais para orientar os estudos."},
        {"title": "Exercism", "body": "Exercícios práticos para aprender linguagens."},
        {"title": "DevDocs", "body": "Documentação técnica pesquisável."},
        {"title": "Regex101", "body": "Teste expressões regulares."},
        {"title": "Salva para depois", "body": "ArtiSys — tecnologia sem complicação."}
      ]
    }

## Parâmetros

- topic: tema; obrigatório.
- slide_count: de 2 a 10; padrão 6.
- photo_mode: same (padrão, mesma foto em todo carrossel) ou varied.
- photo_id: opcional, ID numérico de uma fotografia específica do Pixabay, para
  usar um fundo aprovado previamente e manter a mesma composição em novas
  execuções; exige PIXABAY_API_KEY configurada. Não inclui o arquivo original.
- source: auto (Pixabay, se houver chave, com fallback Commons),
  pixabay (chave obrigatória) ou wikimedia (sem chave).
- photo_terms: até 8 termos de busca, preferencialmente em inglês.
- style: reference (padrão, texto grande branco centralizado com contorno preto, sem barra, sem logo e sem degradê), cinematic, minimal ou contrast.
- aspect: 4:5 (padrão no modo reference), 9:16 opcional. Os estilos antigos mantêm 9:16.
- brand: marca (padrão ArtiSys).
- cta: chamada final.
- hashtags: até 10 hashtags.
- items: até 8 objetos opcionais com name, detail e url (HTTPS).
- slides: lista com um title e body por página, se desejar edição manual.
- only_pages: números das páginas que deseja gerar novamente (ex.: [3]);
  o ZIP conterá apenas essas páginas editadas. A seleção da foto é refeita
  pelos termos de busca; em execuções diferentes o fundo pode mudar.

## Fotos Pixabay e licenciamento

Pixabay é opcional: a chave gratuita preexistente no GitHub Secrets deve
ser nomeada PIXABAY_API_KEY. Não armazene ou forneça chaves nos JSONs.
Nenhuma chave é obrigatória para rodar via Wikimedia Commons.

A licença Pixabay Content License permite criar novas obras com
foto + texto + composição, mas proíbe distribuir conteúdo original como
mídia standalone. O ZIP não inclui a foto original. Atribuição não é
obrigatória pelo Pixabay, mas incluímos os créditos. Para Wikimedia,
usamos apenas CC0 ou CC BY devidamente identificadas e registramos os créditos.

Imagens podem conter marcas, pessoas reconhecíveis ou outros direitos;
revisar antes de publicar comercialmente. Consulte
https://pixabay.com/service/terms/ e
https://commons.wikimedia.org/wiki/Commons:Licensing.

Pixabay pede cache de buscas de API por 24 horas. O código mantém cache
local por até 24 horas e GitHub Actions restaura um cache diário.

## Segurança e QA

Execução automática somente por commit de um NOVO JSON em
carousel_requests/ na branch main (após merge) ou workflow_dispatch
manual para pedido existente; sem upload automático a TikTok/Instagram.
O acesso GitHub usa permissões contents: read nos jobs.

Executar testes:

    python -m pip install Pillow
    python -m unittest discover -s tests -v

Não há APIs pagas obrigatórias. A execução nos runners do GitHub
está sujeita aos limites gratuitos e às políticas de uso do GitHub.

## Activepieces: carrossel diario em rascunho

Fluxo: https://cloud.activepieces.com/projects/u8hdh20XYn35vxPdcf3Es/flows/fWdrDQbvjJH2TfhDlYgAB

- Every Day, 09:00, timezone America/Sao_Paulo, inclusive fins de semana.
- CODE: rotacao de 10 temas empresariais, 4 sites e 6 slides por dia.
- Tables: salva JSON, legenda, data e status Aguardando render na Fila de Carrosseis.
- GitHub: o workflow carousel.yml aceita workflow_dispatch.inputs.request_json,
  que roda no runner sem criar commits diarios de conteudo.
- Fotos: Pixabay gratuito se a chave existente estiver presente; Commons como fallback.
- Artefatos: 6 imagens JPG + ZIP + legenda + licenciamento, sem postar em redes sociais.

Antes de ativar a geracao automatica das imagens:
1. Conectar GitHub dentro do Activepieces em Settings > Connections > GitHub, via OAuth.
   A conexao GitHub do ChatGPT NAO e a mesma conta no Activepieces.
2. Autorizar merge da PR #3, para o workflow existir na branch main.
3. Adicionar a acao GitHub > Trigger Workflow Dispatch, selecionar
   nutricionistaalmeidavh-spec/moneyPrintTest, workflow carousel.yml e ref main.
   Mapear o input request_json a {{step_1['output'].pedido_json}}.
4. Validar o fluxo completo e habilitar. Nao automatizar postagens em redes sociais.

A etapa editorial do Activepieces esta publicada e ativa diariamente; a etapa GitHub esta desabilitada por falta de conexao OAuth. O codigo continua em PR separada.
Nenhum token ou secret foi alterado.
