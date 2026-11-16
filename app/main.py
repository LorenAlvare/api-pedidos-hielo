"""API de gestión de pedidos de hielo — FastAPI + SQLite.

Ejecutar:  uvicorn app.main:app --reload
Documentación interactiva:  http://127.0.0.1:8000/docs
"""
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import date
from typing import Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import FileResponse

from . import crud
from .database import get_db, init_db
from .schemas import CambioEstado, EstadoPedido, Pedido, PedidoActualizar, PedidoCrear, Producto


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # crea la tabla si no existe
    yield


app = FastAPI(
    title="API de Pedidos de Hielo",
    description="Registro y seguimiento de pedidos de una empresa de hielo.",
    version="1.0.0",
    lifespan=lifespan,
)


def _o_404(pedido: Optional[dict], pedido_id: int) -> dict:
    if pedido is None:
        raise HTTPException(status_code=404, detail=f"No existe el pedido con id {pedido_id}")
    return pedido


STATIC_DIR = Path(__file__).resolve().parent / "static"


@app.get("/", include_in_schema=False)
def pagina_principal():
    """Interfaz web para gestionar los pedidos."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api", tags=["General"])
def estado_api():
    return {"mensaje": "API de Pedidos de Hielo funcionando", "documentacion": "/docs", "version": app.version}


@app.get("/health", tags=["General"])
def health():
    """Chequeo de salud para Elastic Beanstalk / balanceador."""
    return {"status": "ok"}


@app.get("/catalogo", tags=["General"])
def catalogo():
    """Productos y estados válidos."""
    return {"productos": [p.value for p in Producto], "estados": [e.value for e in EstadoPedido]}


@app.post("/pedidos", response_model=Pedido, status_code=status.HTTP_201_CREATED, tags=["Pedidos"])
def crear_pedido(datos: PedidoCrear, db: sqlite3.Connection = Depends(get_db)):
    return crud.crear_pedido(db, datos)


@app.get("/pedidos", response_model=list[Pedido], tags=["Pedidos"])
def listar_pedidos(
    estado: Optional[EstadoPedido] = Query(None, description="Filtrar por estado"),
    cliente: Optional[str] = Query(None, description="Buscar por nombre de cliente (parcial)"),
    fecha_desde: Optional[date] = Query(None, description="Creados desde (AAAA-MM-DD)"),
    fecha_hasta: Optional[date] = Query(None, description="Creados hasta (AAAA-MM-DD)"),
    ordenar_por: Literal["id", "creado_en", "actualizado_en", "estado", "cliente", "cantidad"] = Query(
        "creado_en", description="Campo por el que se ordena"
    ),
    orden: Literal["asc", "desc"] = Query("desc", description="asc = ascendente, desc = descendente"),
    limite: int = Query(100, ge=1, le=500),
    desde: int = Query(0, ge=0),
    db: sqlite3.Connection = Depends(get_db),
):
    """Lista pedidos con filtros (estado, cliente, rango de fechas) y ordenamiento."""
    return crud.listar_pedidos(
        db,
        estado.value if estado else None,
        cliente,
        limite,
        desde,
        ordenar_por,
        orden,
        fecha_desde.isoformat() if fecha_desde else None,
        fecha_hasta.isoformat() if fecha_hasta else None,
    )


@app.get("/pedidos/resumen", tags=["Pedidos"])
def resumen(db: sqlite3.Connection = Depends(get_db)):
    """Cantidad de pedidos por estado."""
    conteo = crud.resumen_por_estado(db)
    por_estado = {e.value: conteo.get(e.value, 0) for e in EstadoPedido}
    return {"total": sum(por_estado.values()), "por_estado": por_estado}


@app.get("/pedidos/{pedido_id}", response_model=Pedido, tags=["Pedidos"])
def obtener_pedido(pedido_id: int, db: sqlite3.Connection = Depends(get_db)):
    return _o_404(crud.obtener_pedido(db, pedido_id), pedido_id)


@app.put("/pedidos/{pedido_id}", response_model=Pedido, tags=["Pedidos"])
def actualizar_pedido(pedido_id: int, datos: PedidoActualizar, db: sqlite3.Connection = Depends(get_db)):
    """Actualiza uno o varios campos del pedido."""
    return _o_404(crud.actualizar_pedido(db, pedido_id, datos), pedido_id)


@app.patch("/pedidos/{pedido_id}/estado", response_model=Pedido, tags=["Pedidos"])
def cambiar_estado(pedido_id: int, cambio: CambioEstado, db: sqlite3.Connection = Depends(get_db)):
    """Cambia solo el estado del pedido (ej. de 'pendiente' a 'en_camino')."""
    return _o_404(crud.actualizar_pedido(db, pedido_id, PedidoActualizar(estado=cambio.estado)), pedido_id)


@app.delete("/pedidos/{pedido_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Pedidos"])
def eliminar_pedido(pedido_id: int, db: sqlite3.Connection = Depends(get_db)):
    if not crud.eliminar_pedido(db, pedido_id):
        raise HTTPException(status_code=404, detail=f"No existe el pedido con id {pedido_id}")
