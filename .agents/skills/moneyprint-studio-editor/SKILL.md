---
name: moneyprint-studio-editor
description: Editor visual mobile-first de cenas, mídias e timeline MoneyPrint Studio
---
# MoneyPrint Studio Editor — P2

1. Abra o painel atual e a aba Studio; não crie novo login/admin.
2. Ao criar um projeto, use \`/api/studio/projects\` protegido pela sessão existente e CSRF.
3. A interface manipula uma cópia local. Salve explicitamente para gerar nova revisão otimista; em conflito HTTP 409, recarregue o projeto.
4. A prévia no navegador é um **storyboard animado**, não prova de resultado MP4 final.
5. Permita reorganizar cenas, editar texto/duração, escolher mídia aprovada, desfazer/refazer, exportar JSON.
6. Salve metadados no D1 ou SQLite self-hosted. Não salve vídeos brutos nem tokens no banco.
7. Não dispare renderização, publicação ou download de mídia automaticamente após editar.
8. Teste telas móveis, teclado, eventos de toque, intervalos de tempo e fronteiras de autenticação.
