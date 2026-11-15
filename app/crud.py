"""Operaciones sobre la tabla de pedidos (Crear, Leer, Actualizar, Eliminar)."""
import sqlite3
from typing import Optional

from .schemas import PedidoActualizar, PedidoCrear

CAMPOS_EDITABLES = ("cliente", "producto", "cantidad", "direccion", "estado")


def _a_dict(fila: Optional[sqlite3.Row]) -> Optional[dict]:
    return dict(fila) if fila else None


def crear_pedido(conn: sqlite3.Connection, datos: PedidoCrear) -> dict:
    cur = conn.execute(
        "INSERT INTO pedidos (cliente, producto, cantidad, direccion, estado) VALUES (?, ?, ?, ?, ?)",
        (datos.cliente, datos.producto.value, datos.cantidad, datos.direccion, datos.estado.value),
    )
    conn.commit()
    return obtener_pedido(conn, cur.lastrowid)


def obtener_pedido(conn: sqlite3.Connection, pedido_id: int) -> Optional[dict]:
    fila = conn.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
    return _a_dict(fila)


def listar_pedidos(
    conn: sqlite3.Connection,
    estado: Optional[str] = None,
    cliente: Optional[str] = None,
    limite: int = 100,
    desde: int = 0,
) -> list[dict]:
    sql = "SELECT * FROM pedidos WHERE 1=1"
    params: list = []
    if estado:
        sql += " AND estado = ?"
        params.append(estado)
    if cliente:
        sql += " AND cliente LIKE ?"
        params.append(f"%{cliente}%")
    sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params += [limite, desde]
    return [dict(f) for f in conn.execute(sql, params).fetchall()]


def actualizar_pedido(conn: sqlite3.Connection, pedido_id: int, datos: PedidoActualizar) -> Optional[dict]:
    cambios = {
        k: (v.value if hasattr(v, "value") else v)
        for k, v in datos.model_dump(exclude_unset=True).items()
        if k in CAMPOS_EDITABLES and v is not None
    }
    if not obtener_pedido(conn, pedido_id):
        return None
    if cambios:
        asignaciones = ", ".join(f"{campo} = ?" for campo in cambios)
        conn.execute(
            f"UPDATE pedidos SET {asignaciones}, actualizado_en = datetime('now', 'localtime') WHERE id = ?",
            (*cambios.values(), pedido_id),
        )
        conn.commit()
    return obtener_pedido(conn, pedido_id)


def eliminar_pedido(conn: sqlite3.Connection, pedido_id: int) -> bool:
    cur = conn.execute("DELETE FROM pedidos WHERE id = ?", (pedido_id,))
    conn.commit()
    return cur.rowcount > 0


def resumen_por_estado(conn: sqlite3.Connection) -> dict:
    filas = conn.execute("SELECT estado, COUNT(*) AS total FROM pedidos GROUP BY estado").fetchall()
    return {f["estado"]: f["total"] for f in filas}
