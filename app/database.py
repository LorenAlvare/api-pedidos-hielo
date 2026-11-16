"""Conexión y creación de la base de datos SQLite."""
import os
import sqlite3
from pathlib import Path

# Se puede cambiar con la variable de entorno PEDIDOS_DB (útil para pruebas)
DB_PATH = os.getenv("PEDIDOS_DB", str(Path(__file__).resolve().parent.parent / "pedidos_hielo.db"))

ESQUEMA = """
CREATE TABLE IF NOT EXISTS pedidos (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente        TEXT    NOT NULL,
    producto       TEXT    NOT NULL,
    cantidad       INTEGER NOT NULL CHECK (cantidad > 0),
    direccion      TEXT    NOT NULL,
    estado         TEXT    NOT NULL DEFAULT 'pendiente',
    creado_en      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    actualizado_en TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_pedidos_estado ON pedidos (estado);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # filas accesibles como diccionario
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(ESQUEMA)


def get_db():
    """Dependencia de FastAPI: abre una conexión por petición y la cierra al terminar."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()
