# Service Desk Flask (RBAC)

Sistema corporativo de chamados com níveis de acesso:
- `USER` (abre e acompanha próprios chamados)
- `SUPPORT` (atende chamados)
- `ADMIN` (gestão total)

## Stack
- Flask
- Flask-Login
- Flask-SQLAlchemy
- SQLite (compatível com troca via `DATABASE_URL`)
- python-dotenv
- Bootstrap 5

## Estrutura
- `app.py` (rotas + inicialização)
- `models.py` (models e relacionamentos)
- `auth_utils.py` (decorator `role_required`)
- `email_utils.py` (env + `send_email`)
- `templates/`
- `static/`

## Como rodar (Windows)
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python app.py
```
Abrir: `http://127.0.0.1:5000`

## Usuário admin padrão
Na inicialização, se não existir ADMIN:
- email: `admin@local`
- senha: `admin123`

> Troque a senha imediatamente.

## Perfis e permissões
### USER
- Acessa `GET /meus_chamados`
- Abre chamado em `GET/POST /chamado/novo`
- Vê detalhe em `GET /chamado/<id>` (somente próprios)
- Comenta em `POST /chamado/<id>/comentario`

### SUPPORT
- Acessa `GET /suporte/chamados`
- Detalhe `GET /suporte/chamado/<id>`
- Atualiza status `POST /suporte/chamado/<id>/status`
- Atribui técnico `POST /suporte/chamado/<id>/atribuir`
- Comenta (público/interno) `POST /suporte/chamado/<id>/comentario`

### ADMIN
- Dashboard `GET /admin/dashboard`
- Usuários (CRUD + ativar/desativar)
- Setores (CRUD com bloqueio de exclusão se vinculado)
- Acesso também a chamados (`/admin/chamados` -> painel suporte)

## SMTP (.env)
Variáveis:
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASS`
- `SMTP_USE_TLS`
- `SUPPORT_EMAIL`

### Exemplo Gmail (senha de app)
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu_email@gmail.com
SMTP_PASS=sua_senha_de_app
SMTP_USE_TLS=true
SUPPORT_EMAIL=suporte@empresa.com
```

### Exemplo Office365 / Outlook
```env
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=seu_email@empresa.com
SMTP_PASS=sua_senha
SMTP_USE_TLS=true
SUPPORT_EMAIL=suporte@empresa.com
```

## Notificações por e-mail
- Ao abrir chamado: envia para solicitante e suporte
- Ao status virar `Resolvido`/`Fechado`: envia para solicitante
- Ao atribuir técnico: envia para solicitante

Se envio falhar, o chamado continua normalmente (erro apenas no log/console).
