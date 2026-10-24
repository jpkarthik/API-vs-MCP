"""SQLite persistence for support tickets."""

import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).with_name("tickets.db")


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                subject TEXT NOT NULL,
                description TEXT NOT NULL,
                priority TEXT NOT NULL CHECK (priority IN ('low', 'normal', 'high')),
                status TEXT NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open', 'in_progress', 'closed')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def create_ticket(values: dict[str, Any]) -> dict[str, Any]:
    with connect() as connection:
        cursor = connection.execute(
            """INSERT INTO tickets (customer_name, subject, description, priority)
               VALUES (:customer_name, :subject, :description, :priority)""",
            values,
        )
        row = connection.execute("SELECT * FROM tickets WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return dict(row)


def list_tickets(status: str | None = None) -> list[dict[str, Any]]:
    with connect() as connection:
        if status is None:
            rows = connection.execute("SELECT * FROM tickets ORDER BY id").fetchall()
        else:
            rows = connection.execute(
                "SELECT * FROM tickets WHERE status = ? ORDER BY id", (status,)
            ).fetchall()
        return [dict(row) for row in rows]


def get_ticket(ticket_id: int) -> dict[str, Any] | None:
    with connect() as connection:
        row = connection.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        return row_to_dict(row)


def update_ticket_status(ticket_id: int, status: str) -> dict[str, Any] | None:
    with connect() as connection:
        cursor = connection.execute(
            "UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id)
        )
        if cursor.rowcount == 0:
            return None
        row = connection.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        return row_to_dict(row)


init_db()
