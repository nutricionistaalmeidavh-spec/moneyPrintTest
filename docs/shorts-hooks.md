# Ganchos virais — workflow Shorts do MoneyPrint

O fluxo guarda **110 MP4s sem edição** em um GitHub Release **rascunho**
`shorts-hooks-v1` do próprio repositório. São os 100 cortes adicionais mais
os 10 iniciais. Os binários não entram no histórico do Git, preservando clones
pequenos e evitando Git LFS/serviços pagos. Arquivos de releases não dependem
da retenção curta dos artifacts de GitHub Actions.

## Seleção para Shorts

`.github/workflows/shorts.yml` é o workflow reutilizável de preparação.
Selecione em **Actions → MoneyPrint Shorts — selecionar gancho existente →
Run workflow** uma categoria (`all`, `crash`, `funny`, `sports`, `water`).

1. Lê `CATALOGO.json` do release rascunho.
2. Faz rodízio determinístico pelo número da execução.
3. Baixa **apenas o MP4 escolhido** do release, sem baixar os demais 109.
4. Confere SHA256 e decodificação com FFprobe.
5. Disponibiliza `gancho.mp4`, `selecao.json` e catálogo como artifact de
   preparação. **Não renderiza um Short**, não publica e não adiciona legendas.

O editor `scripts/tutorial_editor.py` aceita `--hook-source` apontando para
`gancho.mp4`, quando uma receita compatível com a resolução, corte e máscaras
de privacidade for fornecida em uma etapa de renderização separada.

## Armazenamento

O release `shorts-hooks-v1` é mantido como **rascunho**: o repositório
atual é público, mas o direito de redistribuição das gravações virais
baixadas de terceiros ainda não foi verificado. Os clipes não devem ser
publicados como biblioteca pública nem utilizados comercialmente sem
confirmar os direitos pertinentes. A ferramenta de preparação pode ser
usada internamente. **Não publicar o release por engano.**

`.github/workflows/publish-shorts-hooks.yml` prepara o release diretamente
dos artifacts de coleta históricos (100 + 10). Para reconstruir uma nova
versão depois do prazo de retenção desses artifacts, será necessária uma nova
coleta ou uma cópia autorizada dos MP4s. O release já criado não depende dos
artifacts de origem.

Nenhum segredo, OAuth, variáveis existentes ou workflows de vídeos longos
foi alterado. Infraestrutura: FFprobe/FFmpeg, Python, GitHub Actions e
Releases, sem APIs comerciais obrigatórias. Custos/limites de Actions são os
do plano GitHub da conta.
