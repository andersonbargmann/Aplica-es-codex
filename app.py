"""Aplicação Flask para controle de empréstimos de notebooks."""

from __future__ import annotations

import csv
from datetime import datetime
from io import StringIO

from flask import Flask, Response, flash, redirect, render_template, request, url_for

from models import (
    delete_agendamento,
    get_agendamento,
    init_db,
    insert_agendamento,
    list_agendamentos,
    update_agendamento,
)

app = Flask(__name__)
app.config["SECRET_KEY"] = "troque-esta-chave-em-producao"

STATUS_OPTIONS = ["Agendado", "Retirado", "Devolvido"]


def normalize_checkbox(name: str) -> int:
    """Converte checkbox HTML em 1/0 para persistência no banco."""
    return 1 if request.form.get(name) == "on" else 0


def parse_form_data() -> tuple[dict, list[str]]:
    """Lê, normaliza e valida os dados enviados no formulário."""
    errors: list[str] = []

    retirada = request.form.get("retirada", "").strip()
    devolucao = request.form.get("devolucao", "").strip()
    marca = request.form.get("marca", "").strip()
    modelo = request.form.get("modelo", "").strip()
    usuario = request.form.get("usuario", "").strip()
    evento = request.form.get("evento", "").strip()
    observacoes = request.form.get("observacoes", "").strip()
    status = request.form.get("status", "Agendado").strip()

    required_fields = {
        "Data e hora da retirada": retirada,
        "Data e hora da devolução": devolucao,
        "Marca": marca,
        "Modelo": modelo,
        "Usuário": usuario,
        "Evento": evento,
    }

    for label, value in required_fields.items():
        if not value:
            errors.append(f"O campo '{label}' é obrigatório.")

    retirada_dt = None
    devolucao_dt = None

    if retirada:
        try:
            retirada_dt = datetime.strptime(retirada, "%Y-%m-%dT%H:%M")
        except ValueError:
            errors.append("Formato inválido para retirada.")

    if devolucao:
        try:
            devolucao_dt = datetime.strptime(devolucao, "%Y-%m-%dT%H:%M")
        except ValueError:
            errors.append("Formato inválido para devolução.")

    if retirada_dt and devolucao_dt and devolucao_dt < retirada_dt:
        errors.append("A data/hora de devolução não pode ser anterior à retirada.")

    regua_extensao = normalize_checkbox("regua_extensao")
    regua_quantidade = request.form.get("regua_quantidade", "").strip()

    if regua_extensao:
        if not regua_quantidade:
            errors.append(
                "Informe a quantidade de régua/extensão quando esse acessório estiver marcado."
            )
        else:
            try:
                regua_quantidade_int = int(regua_quantidade)
                if regua_quantidade_int <= 0:
                    errors.append("A quantidade de régua/extensão deve ser maior que zero.")
            except ValueError:
                errors.append("A quantidade de régua/extensão deve ser numérica.")

    if status not in STATUS_OPTIONS:
        errors.append("Status inválido.")

    data = {
        "retirada": retirada,
        "devolucao": devolucao,
        "marca": marca,
        "modelo": modelo,
        "usuario": usuario,
        "evento": evento,
        "mouse_sem_fio": normalize_checkbox("mouse_sem_fio"),
        "mouse_com_fio": normalize_checkbox("mouse_com_fio"),
        "teclado_sem_fio": normalize_checkbox("teclado_sem_fio"),
        "teclado_com_fio": normalize_checkbox("teclado_com_fio"),
        "carregador": normalize_checkbox("carregador"),
        "apresentador": normalize_checkbox("apresentador"),
        "regua_extensao": regua_extensao,
        "regua_quantidade": int(regua_quantidade) if regua_extensao and regua_quantidade.isdigit() else None,
        "observacoes": observacoes,
        "status": status,
    }
    return data, errors


@app.template_filter("format_datetime")
def format_datetime(value: str) -> str:
    """Exibe datas no padrão brasileiro amigável."""
    if not value:
        return ""
    try:
        dt = datetime.strptime(value, "%Y-%m-%dT%H:%M")
        return dt.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return value


@app.template_filter("accessories_text")
def accessories_text(agendamento: dict) -> str:
    """Converte flags de acessórios em texto legível na tabela."""
    names = []
    mapping = {
        "mouse_sem_fio": "Mouse sem fio",
        "mouse_com_fio": "Mouse com fio",
        "teclado_sem_fio": "Teclado sem fio",
        "teclado_com_fio": "Teclado com fio",
        "carregador": "Carregador",
        "apresentador": "Apresentador",
    }
    for key, label in mapping.items():
        if agendamento[key]:
            names.append(label)
    if agendamento["regua_extensao"]:
        qty = agendamento["regua_quantidade"] or 0
        names.append(f"Régua/extensão ({qty})")
    return ", ".join(names) if names else "Nenhum"


@app.route("/")
def index() -> str:
    """Tela inicial com filtro por usuário/evento e ordenação por retirada."""
    search = request.args.get("search", "")
    agendamentos = list_agendamentos(search)
    return render_template("index.html", agendamentos=agendamentos, search=search)


@app.route("/novo", methods=["GET", "POST"])
def novo_agendamento() -> str:
    """Formulário para criação de novos agendamentos."""
    if request.method == "POST":
        data, errors = parse_form_data()
        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template(
                "form.html",
                agendamento=request.form,
                status_options=STATUS_OPTIONS,
                page_title="Novo agendamento",
                action_label="Salvar",
            )

        insert_agendamento(data)
        flash("Agendamento criado com sucesso!", "success")
        return redirect(url_for("index"))

    return render_template(
        "form.html",
        agendamento=None,
        status_options=STATUS_OPTIONS,
        page_title="Novo agendamento",
        action_label="Salvar",
    )


@app.route("/editar/<int:agendamento_id>", methods=["GET", "POST"])
def editar_agendamento(agendamento_id: int) -> str:
    """Permite edição completa de um agendamento existente."""
    agendamento = get_agendamento(agendamento_id)
    if not agendamento:
        flash("Agendamento não encontrado.", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        data, errors = parse_form_data()
        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template(
                "form.html",
                agendamento=request.form,
                status_options=STATUS_OPTIONS,
                page_title="Editar agendamento",
                action_label="Atualizar",
            )

        update_agendamento(agendamento_id, data)
        flash("Agendamento atualizado com sucesso!", "success")
        return redirect(url_for("index"))

    return render_template(
        "form.html",
        agendamento=agendamento,
        status_options=STATUS_OPTIONS,
        page_title="Editar agendamento",
        action_label="Atualizar",
    )


@app.post("/excluir/<int:agendamento_id>")
def excluir_agendamento(agendamento_id: int):
    """Exclui um agendamento por ID."""
    delete_agendamento(agendamento_id)
    flash("Agendamento excluído com sucesso!", "warning")
    return redirect(url_for("index"))


@app.get("/exportar-csv")
def exportar_csv() -> Response:
    """Exporta todos os agendamentos em CSV."""
    agendamentos = list_agendamentos()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "ID",
            "Usuário",
            "Marca",
            "Modelo",
            "Evento",
            "Retirada",
            "Devolução",
            "Acessórios",
            "Observações",
            "Status",
        ]
    )

    for item in agendamentos:
        writer.writerow(
            [
                item["id"],
                item["usuario"],
                item["marca"],
                item["modelo"],
                item["evento"],
                format_datetime(item["retirada"]),
                format_datetime(item["devolucao"]),
                accessories_text(item),
                item["observacoes"] or "",
                item["status"],
            ]
        )

    csv_content = output.getvalue()
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=agendamentos.csv"},
    )


if __name__ == "__main__":
    # Inicializa a base automaticamente na primeira execução.
    init_db()
    app.run(debug=True)
