# API de Pedidos de Hielo (Python + FastAPI + SQLite)

API REST básica para registrar y gestionar los pedidos de una empresa de hielo.
Cada pedido guarda: **cliente, producto, cantidad, dirección y estado**.

## Estructura

```
api-python/
├── app/
│   ├── main.py       # Endpoints de FastAPI
│   ├── schemas.py    # Modelos y validaciones (Pydantic)
│   ├── crud.py       # Consultas a la base de datos
│   └── database.py   # Conexión SQLite y creación de la tabla
├── tests/test_api.py # Pruebas automáticas
├── infra/beanstalk.yml # CloudFormation: aplicación y entornos de Elastic Beanstalk
├── infra/pipeline.yml # Alternativa: CodePipeline + CodeBuild + Elastic Beanstalk
├── scripts/crear_beanstalk.sh # Crea los entornos desde CloudShell
├── scripts/desplegar.sh # Alternativa con CodePipeline
├── docs/GUIA_AWS.md  # Guía paso a paso
├── buildspec.yml     # Pasos de CodeBuild (instalar, probar, empaquetar)
├── Procfile          # Cómo arranca la app en Elastic Beanstalk
└── requirements.txt
```

## Cómo ejecutarla

```bash
cd api-python
python -m venv venv
# Windows:  venv\Scripts\activate      Linux/Mac:  source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

- **Interfaz web:** http://127.0.0.1:8000 — registrar pedidos, ver el resumen por estado, cambiar estados, buscar y eliminar
- Documentación interactiva de la API (Swagger): http://127.0.0.1:8000/docs

La base de datos `pedidos_hielo.db` se crea sola la primera vez.

## Endpoints

| Método | Ruta                     | Qué hace                                          |
|--------|--------------------------|---------------------------------------------------|
| GET    | `/`                      | Interfaz web                                      |
| GET    | `/catalogo`              | Lista productos y estados válidos                 |
| POST   | `/pedidos`               | Registra un pedido                                |
| GET    | `/pedidos`               | Lista pedidos. Filtros: `estado`, `cliente`, `fecha_desde`, `fecha_hasta`. Orden: `ordenar_por` (`creado_en`, `estado`, `cliente`, `cantidad`, `id`) y `orden` (`asc`/`desc`) |
| GET    | `/health`                | Chequeo de salud (usado en el despliegue)         |
| GET    | `/pedidos/resumen`       | Total de pedidos por estado                       |
| GET    | `/pedidos/{id}`          | Consulta un pedido                                |
| PUT    | `/pedidos/{id}`          | Actualiza uno o varios campos                     |
| PATCH  | `/pedidos/{id}/estado`   | Cambia solo el estado                             |
| DELETE | `/pedidos/{id}`          | Elimina un pedido                                 |

**Productos:** Bolsa de hielo 2 kg · Bolsa de hielo 5 kg · Bolsa de hielo 10 kg · Bloque de hielo 25 kg · Hielo frappé 5 kg · Hielo seco 1 kg

**Estados:** `pendiente` (por defecto) → `en_preparacion` → `en_camino` → `entregado` · `cancelado`

## Ejemplo

```bash
curl -X POST http://127.0.0.1:8000/pedidos \
  -H "Content-Type: application/json" \
  -d '{"cliente":"Restaurante El Polo","producto":"Bolsa de hielo 5 kg","cantidad":20,"direccion":"Calle 45 # 12-30, Bogotá"}'

curl -X PATCH http://127.0.0.1:8000/pedidos/1/estado \
  -H "Content-Type: application/json" -d '{"estado":"en_camino"}'
```

Datos inválidos (cantidad 0, producto inexistente, cliente vacío, estado desconocido) devuelven **422** con el detalle del error; un pedido que no existe devuelve **404**.

## Pruebas

```bash
pytest -v
```

## CI/CD en AWS

```
git push (GitHub) ─► GitHub Actions: pytest ─► app.zip a S3 ─► Elastic Beanstalk PRUEBAS ─► Elastic Beanstalk PRODUCCIÓN
```

El laboratorio de AWS Academy no permite crear CodeBuild ni CodePipeline, así que el CI/CD corre en GitHub Actions
(`.github/workflows/main.yml`) y despliega en Elastic Beanstalk, creado con CloudFormation (`infra/beanstalk.yml`):

```bash
# En AWS CloudShell, una sola vez
git clone https://github.com/LorenAlvare/api-pedidos-hielo.git && cd api-pedidos-hielo
bash scripts/crear_beanstalk.sh
```

Luego se cargan las credenciales del laboratorio como secretos de GitHub. Guía completa (secretos, demo,
capturas para el informe y la alternativa con CodePipeline + CodeBuild): [docs/GUIA_AWS.md](docs/GUIA_AWS.md).

Ejemplo de ordenamiento: `GET /pedidos?ordenar_por=creado_en&orden=asc&estado=pendiente`
