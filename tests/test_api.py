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


def test_ordenar_y_filtrar():
    with TestClient(app) as c:
        ids = [c.post("/pedidos", json={**PEDIDO, "cliente": n, "cantidad": q}).json()["id"]
               for n, q in (("Zeta Bar", 5), ("Alfa Hotel", 50))]
        nombres = [p["cliente"] for p in c.get("/pedidos", params={"ordenar_por": "cliente", "orden": "asc"}).json()]
        assert nombres.index("Alfa Hotel") < nombres.index("Zeta Bar")
        cant = [p["cantidad"] for p in c.get("/pedidos", params={"ordenar_por": "cantidad", "orden": "desc"}).json()]
        assert cant == sorted(cant, reverse=True)
        hoy = c.get(f"/pedidos/{ids[0]}").json()["creado_en"][:10]
        assert len(c.get("/pedidos", params={"fecha_desde": hoy, "fecha_hasta": hoy}).json()) >= 2
        assert c.get("/pedidos", params={"fecha_hasta": "2000-01-01"}).json() == []
        assert c.get("/pedidos", params={"ordenar_por": "contrasena"}).status_code == 422
        assert c.get("/health").json() == {"status": "ok"}


def test_validaciones():
    with TestClient(app) as c:
        assert c.post("/pedidos", json={**PEDIDO, "cantidad": 0}).status_code == 422
        assert c.post("/pedidos", json={**PEDIDO, "producto": "Hielo raro"}).status_code == 422
        assert c.post("/pedidos", json={**PEDIDO, "cliente": "   "}).status_code == 422
        assert c.post("/pedidos", json={**PEDIDO, "estado": "perdido"}).status_code == 422
