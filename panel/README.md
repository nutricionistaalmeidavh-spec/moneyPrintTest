# ArtiSys — Central de Automações

Painel mobile-first e open source para disparar o MoneyPrint e consultar execuções do GitHub Actions sem depender do ChatGPT.

**Cloudflare (implantado):** https://artisys-flow-panel.nutricionistaalmeidavh.workers.dev

## Recursos

- Login com senha forte (hash SHA-256), HMAC, cookie Secure/HttpOnly/SameSite Strict e proteção CSRF.
- Registros de falhas de login e bloqueio temporário por tentativas incorretas.
- Formulário para criar um JSON de pedido em requests/ e iniciar render.yml via o gatilho push existente.
- Disparo manual dos workflows de QA, tutorial revisado e renderização de pedido existente.
- Lista de execuções do GitHub Actions e link para os artifacts.
- Histórico auditável no D1/SQLite.
- Nove fluxos Activepieces inventariados como **somente leitura**, sem disparos manuais.
- Sem autopublicação nas redes sociais.

## Conectar GitHub

No próprio painel: Conexões > Token fine-grained. Crie em https://github.com/settings/personal-access-tokens/new um token dedicado somente a nutricionistaalmeidavh-spec/moneyPrintTest, com permissões Contents: Read and write e Actions: Read and write. Metadata: Read já é incluída pelo GitHub. Não use o token pessoal da conta inteira.

O token é validado no GitHub e criptografado usando AES-GCM antes do armazenamento no D1. Ele não volta para o navegador. Revogue a credencial no GitHub para remover acesso.

A verificação inicial confirma acesso de leitura ao repositório, não comprova escopos de escrita. Se insuficiente, o painel exibe erro ao criar pedido ou disparar workflow.

## Worker Cloudflare

O código fonte está em panel/worker.js. O schema do banco está em panel/schema.sql. O deployment publicado chama-se artisys-flow-panel, com binding D1 DB apontando para artisys-flow-panel.

**Secrets separados**: ADMIN_PASS_HASH (SHA-256 hexadecimal de senha aleatória), SESSION_KEY (32 bytes base64url), ENCRYPTION_KEY (32 bytes base64url). Jamais suba secrets ou tokens no Git.

Para gerar os valores em um shell com Node.js:

    node -e "const c=require('node:crypto');const p=c.randomBytes(24).toString('base64url');console.log('Senha:',p);console.log('ADMIN_PASS_HASH:',c.createHash('sha256').update(p).digest('hex'));console.log('SESSION_KEY:',c.randomBytes(32).toString('base64url'));console.log('ENCRYPTION_KEY:',c.randomBytes(32).toString('base64url'))"

A atualização do Worker pela API Cloudflare usa upload multipart com main_module=worker.js e binding DB. Não misture credenciais com outros Workers.

## Instalação 100% self-hosted sem Cloudflare

O adaptador panel/local-server.mjs usa Node.js 22+ e SQLite integrado, **zero pacotes npm externos**. Banco: schema.sql.

No terminal, configure ADMIN_PASS_HASH, SESSION_KEY, ENCRYPTION_KEY, SQLITE_PATH e PUBLIC_ORIGIN por variáveis de ambiente, depois:

    export SQLITE_PATH=./panel-data/panel.sqlite
    export PUBLIC_ORIGIN=https://painel.seudominio.com
    node panel/local-server.mjs

O servidor escuta 127.0.0.1:8787. Exponha por proxy HTTPS (Caddy/Nginx, open source); o cookie Secure não funciona adequadamente sem HTTPS. Mantenha backups locais do SQLite.

## Limites e transparência

- A execução depende das cotas do GitHub Actions ou de um runner próprio.
- A interface não executa fluxos Activepieces do tipo schedule/tables diretamente. Para habilitar disparo manual, será preciso criar endpoints autenticados específicos sem alterar os agendamentos já existentes.
- Status “solicitado” confirma envio ao GitHub, **não** que o processamento terminou. Confira GitHub Actions recentes.
- O painel não assume publicação automática em plataformas de vídeo.
- O app pode rodar em Cloudflare Free sujeito a cotas, ou de forma própria com custo de software R$ 0.
