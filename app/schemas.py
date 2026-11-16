"""Modelos de datos (validación de entrada y salida) con Pydantic."""
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Producto(str, Enum):
    bolsa_2kg = "Bolsa de hielo 2 kg"
    bolsa_5kg = "Bolsa de hielo 5 kg"
    bolsa_10kg = "Bolsa de hielo 10 kg"
    bloque_25kg = "Bloque de hielo 25 kg"
    frappe_5kg = "Hielo frappé 5 kg"
    seco_1kg = "Hielo seco 1 kg"


class EstadoPedido(str, Enum):
    pendiente = "pendiente"
    en_preparacion = "en_preparacion"
    en_camino = "en_camino"
    entregado = "entregado"
    cancelado = "cancelado"


class _ValidaTextos(BaseModel):
    """Quita espacios al inicio/fin y rechaza textos vacíos."""

    @field_validator("cliente", "direccion", check_fields=False)
    @classmethod
    def no_vacio(cls, v):
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("no puede estar vacío")
        return v


class PedidoCrear(_ValidaTextos):
    cliente: str = Field(..., max_length=120, examples=["Restaurante El Polo"])
    producto: Producto = Field(..., examples=["Bolsa de hielo 5 kg"])
    cantidad: int = Field(..., ge=1, le=10000, examples=[20])
    direccion: str = Field(..., max_length=250, examples=["Calle 45 # 12-30, Bogotá"])
    estado: EstadoPedido = EstadoPedido.pendiente


class PedidoActualizar(_ValidaTextos):
    """Todos los campos son opcionales: solo se cambia lo que se envía."""
    cliente: Optional[str] = Field(None, max_length=120)
    producto: Optional[Producto] = None
    cantidad: Optional[int] = Field(None, ge=1, le=10000)
    direccion: Optional[str] = Field(None, max_length=250)
    estado: Optional[EstadoPedido] = None


class CambioEstado(BaseModel):
    estado: EstadoPedido


class Pedido(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente: str
    producto: Producto
    cantidad: int
    direccion: str
    estado: EstadoPedido
    creado_en: str
    actualizado_en: str
