# Sistema Help Desk TI (Flask)

Aplicação web completa para gestão de chamados de TI com autenticação, perfis de acesso (ADMIN/USER), histórico de mensagens, anexos e envio de e-mails automáticos.

## Tecnologias

- **Backend:** Python + Flask
- **Banco de dados:** SQLite (configurável por `DATABASE_URL` para MySQL/PostgreSQL)
- **Frontend:** HTML + Bootstrap 5 responsivo
- **Autenticação:** Flask-Login + hash seguro com Werkzeug

## Funcionalidades implementadas

- Login com sessão autenticada
- CRUD de usuários internos (somente ADMIN)
- Perfis:
  - **ADMIN:** gerencia usuários e todos os chamados
  - **USER:** abre e acompanha apenas os próprios chamados
- Abertura de chamados com:
  - Categoria, prioridade, assunto, descrição
  - Upload opcional (png/jpg/jpeg/pdf)
  - Criação automática com status inicial `Aberto`
- Painel de chamados com filtros por status, prioridade, categoria e setor
- Busca por ID ou assunto
- Paginação dos chamados
- Atribuição de técnico (usuário ADMIN)
- Atualização de status (Aberto, Em andamento, Resolvido, Fechado)
- Registro de solução final
- Histórico de mensagens (chat por chamado)
- Exportação de chamados para CSV (ADMIN)
- Emails automáticos:
  - Ao abrir chamado (usuário + suporte)
  - Ao atualizar status (usuário)

## Estrutura do projeto

```
app.py
models.py
templates/
static/
uploads/
requirements.txt
.env.example
README.md
```

## Como rodar no Windows

1. Criar e ativar ambiente virtual:
   ```powershell
   python -m venv venv
   venv\Scripts\activate
   ```
2. Instalar dependências:
   ```powershell
   pip install -r requirements.txt
   ```
3. Configurar variáveis de ambiente:
   - Copie `.env.example` para `.env` e ajuste os valores.
4. Executar aplicação:
   ```powershell
   python app.py
   ```
5. Abrir no navegador:
   - `http://127.0.0.1:5000`

## Usuário ADMIN padrão (primeiro start)

No primeiro start, o sistema cria automaticamente:

- **Email:** `admin@local`
- **Senha:** `admin123`

> **Importante:** altere essa senha imediatamente após o primeiro acesso.

## Configuração SMTP (.env)

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASS`
- `SMTP_TLS`
- `EMAIL_SUPORTE`

Se SMTP não estiver configurado, a aplicação continua funcionando e apenas registra aviso no log quando o envio falhar.

## Banco de dados

A aplicação cria automaticamente as tabelas ao iniciar:

- `users`
- `tickets`
- `ticket_messages`
- `attachments`

Por padrão usa SQLite (`sqlite:///helpdesk.db`), mas você pode mudar para MySQL/PostgreSQL alterando `DATABASE_URL`.
