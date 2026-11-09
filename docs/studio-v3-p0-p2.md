# MoneyPrint Studio V3 — P0/P1/P2

## Escopo real

**P0 — contrato e compatibilidade:** \`schemas/video-project-v3.schema.json\`, \`scripts/studio_project.py\`, migração aditiva D1/SQLite, revisão otimista. Render legado intacto.

**P1 — análise e storyboard:** \`scripts/reference_analyzer.py\` usa FFprobe e FFmpeg locais para medir duração, cortes e cadência; OpenCV opcional estima região de detalhes do frame com **baixa confiança**, sem fingir identificação semântica de sujeitos. \`create_project\` segmenta roteiro por frases e distribui frames sem lacunas. \`rank_assets\` somente seleciona mídia previamente aprovada, com licença, crédito e caminho local seguro.

**P2 — editor mobile:** aba Studio dentro do painel existente, com storyboard pré-visualizável no navegador, timeline horizontal, edição de texto/duração/transição, ordem das cenas, biblioteca de mídia, desfazer/refazer, export JSON e salvamento explícito com conflito de revisão HTTP 409.

**O que P0–P2 não entregam:** exportação MP4 diretamente da timeline V3, keyframes complexos, alinhamento real por palavra, reenquadramento inteligente, detecção semântica de enquadramentos ou QA avançado; pertencem às próximas fases P3–P5. A prévia é uma representação gráfica do storyboard, não é o MP4 final.

## Core self-hosted R$ 0

O core não usa Remotion comercial nem APIs pagas. Requisitos: Python 3.11+, FFmpeg/FFprobe para análise de referências, Node 22+ para painel, SQLite local. O banco Cloudflare D1 é adaptador opcional. Referências permanecem locais; o relatório JSON não contém o vídeo.

\`\`\`bash
python -m scripts.studio_cli storyboard --input roteiro.txt --topic "Tutorial GitHub" --duration 120 --aspect 9:16 --output storyboard.json
python -m scripts.studio_cli reference --input assets/referencia.mp4 --output referencia.json
python -m scripts.studio_cli validate --input storyboard.json
node --test panel/test.mjs panel/studio.test.mjs
python -m unittest discover -s tests -v
\`\`\`

Para análise focal com heurística, pode-se instalar o OpenCV (opcional). O relatório distingue \`ffmpeg_scene_select\` factual de \`edge_density_heuristic\` de baixa confiança.

## Panel / Studio

O painel existente \`panel/worker.js\` serve a aba Studio com a mesma autenticação e CSRF. Após login:

1. Crie um storyboard informando tema, roteiro, duração e formato.
2. Selecione uma cena na timeline, edite título/texto/duração ou reorganize as cenas.
3. Adicione somente mídias com licença e atribuição, existentes em \`assets/\` no executor.
4. Use a prévia gráfica e **Salvar revisão**. As alterações são locais até salvar.
5. Exportar JSON salva o contrato V3. **Não dispara render automaticamente**, nem afirma equivalência com MP4.

Endpoints autenticados: \`GET/POST /api/studio/projects\`, \`GET /api/studio/projects/:id\`, \`POST /api/studio/projects/:id/save\`. O projeto é persistido em \`studio_projects\` e \`studio_revisions\`. Todos os POSTs usam a proteção de origem e CSRF existentes. A atualização é condicional por revisão (HTTP 409 para conflito).

## Segurança e migração

- SQL aditivo em \`panel/schema.sql\`; também inicializado sob demanda pelo backend Studio após autenticação.
- Tokens GitHub, OAuth, secrets, preços e jobs de renderização permanecem inalterados.
- Caminhos de mídia restringidos ao diretório \`assets/\` com rejeição de \`..\`. A existência real e a licença devem ser confirmadas antes de qualquer uso na produção.
- Não são enviados vídeos brutos à Cloudflare; o Studio guarda apenas metadados de cenas e arquivos.
- A validação da timeline exige durações positivas e ausência de sobreposição ou lacuna.
- Antes de publicar Worker, executar QA real do painel e confirmar migração D1 no ambiente de destino; não implantar cegamente.

## Compatibilidade e limites

O \`to_render_request\` gera pedido do motor legado de forma separada e limitada; ele **não transforma** a timeline V3 em MP4 frame-exato. Esse vínculo com o renderizador entrará no P3. O painel legado tem validação de duração distinta do CLI de vídeo; corrigir numa etapa separada após teste de limites do executor. Não ampliar artificialmente cotas de Actions.

## QA

- Testes Python para distribuição de frames, seleção de mídia, edição, conflitos e estatísticas de referência.
- Testes Node para sessão, CSRF, CRUD/revisão e limites de tempo.
- Para QA manual, abrir aba Studio em desktop e mobile, editar rascunhos, recarregar, confirmar persistência e ausência de mutações em rotas legadas.
