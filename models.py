"""Módulo de acesso a dados da aplicação de empréstimos de TI."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "agendamentos.db"


def get_connection() -> sqlite3.Connection:
    """Retorna uma conexão SQLite com rows acessíveis por nome de coluna."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    """Cria a tabela principal automaticamente na primeira execução."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agendamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                retirada TEXT NOT NULL,
                devolucao TEXT NOT NULL,
                marca TEXT NOT NULL,
                modelo TEXT NOT NULL,
                usuario TEXT NOT NULL,
                evento TEXT NOT NULL,
                mouse_sem_fio INTEGER NOT NULL DEFAULT 0,
                mouse_com_fio INTEGER NOT NULL DEFAULT 0,
                teclado_sem_fio INTEGER NOT NULL DEFAULT 0,
                teclado_com_fio INTEGER NOT NULL DEFAULT 0,
                carregador INTEGER NOT NULL DEFAULT 0,
                apresentador INTEGER NOT NULL DEFAULT 0,
                regua_extensao INTEGER NOT NULL DEFAULT 0,
                regua_quantidade INTEGER,
                observacoes TEXT,
                status TEXT NOT NULL DEFAULT 'Agendado'
            )
            """
        )


def insert_agendamento(data: dict[str, Any]) -> None:
    """Insere um novo agendamento na base."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO agendamentos (
                retirada, devolucao, marca, modelo, usuario, evento,
                mouse_sem_fio, mouse_com_fio, teclado_sem_fio, teclado_com_fio,
                carregador, apresentador, regua_extensao, regua_quantidade,
                observacoes, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["retirada"],
                data["devolucao"],
                data["marca"],
                data["modelo"],
                data["usuario"],
                data["evento"],
                data["mouse_sem_fio"],
                data["mouse_com_fio"],
                data["teclado_sem_fio"],
                data["teclado_com_fio"],
                data["carregador"],
                data["apresentador"],
                data["regua_extensao"],
                data["regua_quantidade"],
                data["observacoes"],
                data["status"],
            ),
        )


def update_agendamento(agendamento_id: int, data: dict[str, Any]) -> None:
    """Atualiza um agendamento existente."""
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE agendamentos
               SET retirada = ?,
                   devolucao = ?,
                   marca = ?,
                   modelo = ?,
                   usuario = ?,
                   evento = ?,
                   mouse_sem_fio = ?,
                   mouse_com_fio = ?,
                   teclado_sem_fio = ?,
                   teclado_com_fio = ?,
                   carregador = ?,
                   apresentador = ?,
                   regua_extensao = ?,
                   regua_quantidade = ?,
                   observacoes = ?,
                   status = ?
             WHERE id = ?
            """,
            (
                data["retirada"],
                data["devolucao"],
                data["marca"],
                data["modelo"],
                data["usuario"],
                data["evento"],
                data["mouse_sem_fio"],
                data["mouse_com_fio"],
                data["teclado_sem_fio"],
                data["teclado_com_fio"],
                data["carregador"],
                data["apresentador"],
                data["regua_extensao"],
                data["regua_quantidade"],
                data["observacoes"],
                data["status"],
                agendamento_id,
            ),
        )


def delete_agendamento(agendamento_id: int) -> None:
    """Remove um agendamento por ID."""
    with get_connection() as conn:
        conn.execute("DELETE FROM agendamentos WHERE id = ?", (agendamento_id,))


def get_agendamento(agendamento_id: int) -> sqlite3.Row | None:
    """Busca um agendamento específico por ID."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM agendamentos WHERE id = ?", (agendamento_id,)
        ).fetchone()


def list_agendamentos(search: str = "") -> list[sqlite3.Row]:
    """Lista agendamentos com filtro opcional por usuário e evento."""
    search = (search or "").strip()
    with get_connection() as conn:
        if search:
            like_term = f"%{search}%"
            return conn.execute(
                """
                SELECT *
                  FROM agendamentos
                 WHERE usuario LIKE ? OR evento LIKE ?
                 ORDER BY datetime(retirada) ASC
                """,
                (like_term, like_term),
            ).fetchall()

        return conn.execute(
            "SELECT * FROM agendamentos ORDER BY datetime(retirada) ASC"
        ).fetchall()
