"""Pruebas de la API. Ejecutar con:  pytest -v"""
import os
import tempfile

os.environ["PEDIDOS_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

PEDIDO = {
    "cliente": "Restaurante El Polo",
    "producto": "Bolsa de hielo 5 kg",
    "cantidad": 20,
    "direccion": "Calle 45 # 12-30, Bogotá",
}


def test_flujo_completo():
    with TestClient(app) as c:
        r = c.post("/pedidos", json=PEDIDO)
        assert r.status_code == 201
        p = r.json()
        assert p["estado"] == "pendiente"

        assert c.get(f"/pedidos/{p['id']}").json()["cliente"] == "Restaurante El Polo"
        assert len(c.get("/pedidos", params={"estado": "pendiente"}).json()) >= 1

        r = c.patch(f"/pedidos/{p['id']}/estado", json={"estado": "en_camino"})
        assert r.json()["estado"] == "en_camino"

        r = c.put(f"/pedidos/{p['id']}", json={"cantidad": 35})
        assert r.json()["cantidad"] == 35 and r.json()["estado"] == "en_camino"

        assert c.get("/pedidos/resumen").json()["por_estado"]["en_camino"] >= 1

        assert c.delete(f"/pedidos/{p['id']}").status_code == 204
        assert c.get(f"/pedidos/{p['id']}").status_code == 404


def test_validaciones():
    with TestClient(app) as c:
        assert c.post("/pedidos", json={**PEDIDO, "cantidad": 0}).status_code == 422
        assert c.post("/pedidos", json={**PEDIDO, "producto": "Hielo raro"}).status_code == 422
        assert c.post("/pedidos", json={**PEDIDO, "cliente": "   "}).status_code == 422
        assert c.post("/pedidos", json={**PEDIDO, "estado": "perdido"}).status_code == 422
