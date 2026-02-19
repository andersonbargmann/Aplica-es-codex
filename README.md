# Controle de Empréstimos de Notebooks (Flask + SQLite)

Aplicação web para agendamento de retirada e devolução de notebooks e acessórios de TI.

## Estrutura do projeto

```text
.
├── app.py
├── models.py
├── requirements.txt
├── agendamentos.db (criado automaticamente)
├── static/
│   └── css/
│       └── styles.css
└── templates/
    ├── base.html
    ├── index.html
    └── form.html
```

## Requisitos

- Python 3.10 ou superior
- Windows PowerShell ou Prompt de Comando

## Como executar no Windows (passo a passo)

1. Abra o terminal na pasta do projeto.
2. Crie o ambiente virtual:

```powershell
python -m venv .venv
```

3. Ative o ambiente virtual:

```powershell
.venv\Scripts\activate
```

4. Instale as dependências:

```powershell
pip install -r requirements.txt
```

5. Execute a aplicação:

```powershell
python app.py
```

6. Acesse no navegador:

- http://127.0.0.1:5000

## Funcionalidades

- CRUD completo de agendamentos (criar, listar, editar, excluir)
- Filtro por usuário e evento
- Ordenação por data de retirada (mais próximo primeiro)
- Controle de status manual: Agendado, Retirado, Devolvido
- Validações de campos obrigatórios
- Validação de devolução não anterior à retirada
- Exportação de todos os agendamentos para CSV
- Banco SQLite persistente com criação automática na primeira execução
