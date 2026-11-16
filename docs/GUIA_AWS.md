# Guía: CI/CD de la API de Pedidos de Hielo en AWS

> El laboratorio de AWS Academy que usamos **no permite crear proyectos de CodeBuild ni pipelines de
> CodePipeline** (`codebuild:CreateProject` y `codepipeline:CreatePipeline` dan *AccessDenied*). Por eso la
> integración y la entrega continua corren en **GitHub Actions** y la aplicación se despliega en
> **AWS Elastic Beanstalk**. Si tu entorno sí permite CodePipeline, mira la alternativa al final.

```
git push a GitHub (rama main)
   └─► GitHub Actions (.github/workflows/main.yml)
         1. Pruebas unitarias ...... pytest + informe JUnit (caché de pip)
         2. Empaquetar ............. app.zip → S3 → nueva versión en Elastic Beanstalk
         3. Desplegar en PRUEBAS ... entorno pedidos-hielo-pruebas + chequeo de /health
         4. Desplegar en PRODUCCIÓN  entorno pedidos-hielo-produccion + chequeo de /health
   Logs de la app ─► CloudWatch Logs
```

Infraestructura como código: `infra/beanstalk.yml` (CloudFormation) crea la aplicación y los dos entornos.

## 1. Crear los entornos de Beanstalk (una sola vez)

Inicia el laboratorio, abre la consola de AWS en **us-east-1** y luego **CloudShell** (ícono `>_`):

```bash
cd ~ && rm -rf api-pedidos-hielo
git clone https://github.com/LorenAlvare/api-pedidos-hielo.git
cd api-pedidos-hielo
bash scripts/crear_beanstalk.sh
```

Tarda unos 10 minutos. Al final muestra `UrlPruebas` y `UrlProduccion`. Si algo falla, el script imprime el motivo.

## 2. Darle a GitHub las credenciales del laboratorio

1. En la página del laboratorio (donde está *Start Lab*) abre **AWS Details** → **AWS CLI: Show**.
   Verás `aws_access_key_id`, `aws_secret_access_key` y `aws_session_token`.
2. En GitHub: repositorio → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.
   Crea estos tres secretos, copiando cada valor sin espacios:

| Secreto | Valor |
|---------|-------|
| `AWS_ACCESS_KEY_ID` | `aws_access_key_id` |
| `AWS_SECRET_ACCESS_KEY` | `aws_secret_access_key` |
| `AWS_SESSION_TOKEN` | `aws_session_token` |

> **Importante:** estas credenciales **cambian cada vez que inicias el laboratorio** (y vencen a las pocas horas).
> Antes de cada demo: *Start Lab* → copia de nuevo los tres valores → actualiza los secretos (botón ✏️ de cada uno).
> Si el workflow falla con `ExpiredToken` o `InvalidClientTokenId`, es eso.

## 3. Primer despliegue

GitHub → pestaña **Actions** → **CI/CD API Pedidos de Hielo** → **Run workflow** (o haz cualquier push a `main`).
Verás los 4 trabajos en verde y, en *Desplegar en PRUEBAS / PRODUCCIÓN*, el enlace a cada URL.
Abre `URL/docs` para probar la API.

### Aprobación manual antes de producción (opcional)

En GitHub: **Settings** → **Environments** → `produccion` → marca **Required reviewers** y agrégate.
Así el despliegue a producción espera a que pulses *Approve* (disponible en repositorios públicos).

## 4. Demostrar el despliegue automático (video)

1. Cambia la versión en `app/main.py` (`version="1.1.0"`) y súbelo:
   ```bash
   git commit -am "Subir versión a 1.1.0" && git push
   ```
2. En GitHub → **Actions** se ve arrancar el workflow solo, con el mensaje del commit.
3. Muestra las pruebas pasando, el despliegue a pruebas, luego producción.
4. En AWS → **Elastic Beanstalk** → *Versiones de la aplicación*: aparece `v<número>-<commit>`.
5. Abre `URL/` en producción: la versión cambió.
6. Extra: sube un cambio que rompa una prueba y muestra que el workflow se detiene en *Pruebas unitarias*
   y no despliega. Luego reviértelo.

## 5. Capturas sugeridas para el informe PDF

| Requisito | Captura |
|-----------|---------|
| Control de versiones | Repositorio en GitHub con el historial de commits |
| Infraestructura como código | CloudFormation: pila `pedidos-hielo-beanstalk` en `CREATE_COMPLETE` + `infra/beanstalk.yml` |
| CI (disparo por commit) | GitHub Actions: ejecución disparada por un push, con el commit |
| Compilación y pruebas | Trabajo *Pruebas unitarias* con pytest en verde + artefacto `informe-pruebas` |
| Artefactos | Artefacto `app` en GitHub y versión de la aplicación en Beanstalk (S3) |
| Caché de dependencias | `cache: pip` en el workflow |
| CD | Trabajos de despliegue a pruebas y producción + entornos en estado *Ok* en Beanstalk |
| Monitoreo | CloudWatch Logs: grupos `/aws/elasticbeanstalk/pedidos-hielo-...` |
| App funcionando | `/docs` en producción: crear, filtrar/ordenar pedidos y cambiar su estado |
| Limitación del laboratorio | Captura del error `not authorized to perform: codepipeline:CreatePipeline` (justifica por qué se usó GitHub Actions) |

## Problemas comunes

| Error | Solución |
|-------|----------|
| `ExpiredToken` / `InvalidClientTokenId` / `security token included in the request is invalid` | Las credenciales del laboratorio cambiaron: actualiza los tres secretos (paso 2). |
| `No Application named 'pedidos-hielo-app'` o `No Environment found` | Falta el paso 1, o el laboratorio se reinició y borró los recursos: vuelve a correr `scripts/crear_beanstalk.sh`. |
| `La API no respondió en /health` | Beanstalk → entorno → *Registros* → *Solicitar registros*. La app arranca con el `Procfile` (uvicorn, puerto 8000). |
| El entorno queda en rojo tras reiniciar el lab | Re-ejecuta el workflow (*Run workflow*). |

## Borrar todo al terminar

```bash
aws cloudformation delete-stack --stack-name pedidos-hielo-beanstalk
```

---

# Alternativa: CodePipeline + CodeBuild (solo si tu entorno lo permite)

Flujo que se monta (todo con una sola plantilla de CloudFormation, `infra/pipeline.yml`):

```
git push a GitHub (rama main)
   └─► CodePipeline
         1. Fuente ............ descarga el código de GitHub
         2. Construcción ...... CodeBuild: instala dependencias, corre pytest, genera el artefacto (buildspec.yml)
         3. DesplegarPruebas .. Elastic Beanstalk, entorno "pedidos-hielo-pruebas"
         4. Aprobación ........ aprobación manual (revisas la API de pruebas)
         5. DesplegarProducción Elastic Beanstalk, entorno "pedidos-hielo-produccion"
   Logs de CodeBuild y de la app ─► CloudWatch Logs
```

No hace falta crear nada a mano en CodeBuild ni en CodePipeline: la plantilla crea todo
(bucket S3, proyecto de CodeBuild, aplicación y entornos de Beanstalk y el pipeline).

### 0. Antes de empezar

- **AWS Academy Learner Lab**: inicia el laboratorio ("Start Lab") y entra a la consola. La plantilla usa
  `LabRole` y `LabInstanceProfile`, que ya existen en el laboratorio. Trabaja en la región **us-east-1**.
- **CodeCommit no se usa**: AWS cerró CodeCommit a cuentas nuevas, por eso la fuente es GitHub.

### 1. Crear un token de GitHub

1. GitHub → foto de perfil → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**.
2. **Generate new token (classic)**, nombre `codepipeline`, marca el permiso **repo** y genéralo.
3. Copia el token (empieza por `ghp_`). Solo se muestra una vez.

### 2. Desplegar la infraestructura (CloudShell)

En la consola de AWS abre **CloudShell** (ícono `>_` arriba) y ejecuta:

```bash
git clone https://github.com/LorenAlvare/api-pedidos-hielo.git
cd api-pedidos-hielo
bash scripts/desplegar.sh
```

El script busca solo la versión vigente de la plataforma de Beanstalk (Python 3.12), te pide el token
y crea la pila `pedidos-hielo`. Tarda unos 10 minutos. Al final muestra las URL de pruebas y producción.

#### Si tu laboratorio no deja crear proyectos de CodeBuild

Algunos laboratorios de AWS Academy bloquean `codebuild:CreateProject`. El error se ve así:
`not authorized to perform: codebuild:CreateProject`. En ese caso elige otro modo de pruebas:

```bash
# Las pruebas corren en una acción "Commands" de CodePipeline (usa CodeBuild por debajo, sin crear proyecto)
MODO_PRUEBAS=Commands bash scripts/desplegar.sh

# Si también se bloquea: CodePipeline solo despliega y las pruebas quedan en GitHub Actions
MODO_PRUEBAS=Ninguno bash scripts/desplegar.sh
```

El script borra solo la pila fallida anterior antes de volver a intentar. Si algo falla, imprime el motivo.

> Alternativa sin CloudShell: **CloudFormation → Crear pila → Cargar un archivo de plantilla** →
> `infra/pipeline.yml`. Llena `TokenGitHub` y `PlataformaBeanstalk` (el nombre exacto sale de
> `aws elasticbeanstalk list-available-solution-stacks`).

### 3. Ver el pipeline en acción

1. **CodePipeline → pedidos-hielo-pipeline**. La primera ejecución arranca sola al crearse.
2. **Construcción** abre CodeBuild: pestaña *Registros de compilación* (salida de pytest) e *Informes*
   (resultado de las pruebas en formato JUnit).
3. Cuando **DesplegarPruebas** termina, abre la URL de pruebas + `/docs` para probar la API.
4. En **Aprobación** pulsa *Revisar* → *Aprobar*. Se despliega a producción.

### 4. Demostrar el despliegue automático (para el video)

1. Haz un cambio visible, por ejemplo la versión en `app/main.py` (`version="1.1.0"`), y súbelo:
   ```bash
   git commit -am "Subir versión a 1.1.0" && git push
   ```
2. En 1-2 minutos el pipeline arranca solo con ese commit (se ve el mensaje del commit en la etapa Fuente).
3. Muestra CodeBuild corriendo las pruebas, el despliegue a pruebas, la aprobación y producción.
4. Abre `URL/` y muestra que la versión cambió.
5. Extra: sube un cambio que rompa una prueba y muestra que el pipeline se detiene en Construcción
   y no llega a desplegarse. Luego reviértelo.

### 5. Capturas sugeridas para el informe PDF

| Requisito | Captura |
|-----------|---------|
| Control de versiones | Repositorio en GitHub con el historial de commits |
| Infraestructura como código | CloudFormation: pila `pedidos-hielo` en `CREATE_COMPLETE` y pestaña *Recursos* |
| CI con CodePipeline | Pipeline con todas las etapas en verde y el commit que lo disparó |
| CodeBuild | Registro con `pytest` pasando + pestaña *Informes* + `buildspec.yml` |
| Caché de dependencias | Sección `cache` del `buildspec.yml` |
| CD (opcional) | Entornos de pruebas y producción en Beanstalk en estado *Ok* + la aprobación manual |
| Monitoreo | CloudWatch Logs: grupo `/codebuild/pedidos-hielo` y logs del entorno de Beanstalk |
| App funcionando | `/docs` en producción creando, filtrando/ordenando pedidos y cambiando su estado |

### Problemas comunes

| Error | Solución |
|-------|----------|
| `not authorized to perform: codebuild:CreateProject` | El laboratorio no deja crear proyectos de CodeBuild. Usa `MODO_PRUEBAS=Commands` (ver sección 2). |
| `Cannot have more than 0 builds in queue` | Límite de CodeBuild de cuentas nuevas. Pide aumento en *Service Quotas* o abre un caso de soporte; en Learner Lab reinicia el lab y prueba de nuevo. |
| La etapa Fuente falla con el token | Revisa que el token tenga permiso `repo` y no haya vencido. Si sigue fallando, crea una conexión en **Developer Tools → Settings → Connections → GitHub**, autorízala y vuelve a desplegar con `ArnConexion=<arn>` en vez del token. |
| `No Solution Stack named ...` | La versión de la plataforma cambió. Usa `scripts/desplegar.sh`, que la busca sola. |
| Beanstalk en rojo (*Severe*) | Revisa *Registros* del entorno. La app arranca con el `Procfile` (`uvicorn` en el puerto 8000) y el chequeo de salud es `/health`. |
| El laboratorio se cerró | Al reiniciar Learner Lab, la pila sigue; si los entornos quedaron detenidos, vuelve a ejecutar el pipeline con *Liberar cambio*. |

### Borrar todo al terminar

```bash
aws s3 rm s3://$(aws cloudformation describe-stack-resource --stack-name pedidos-hielo \
  --logical-resource-id BucketArtefactos --query StackResourceDetail.PhysicalResourceId --output text) --recursive
aws cloudformation delete-stack --stack-name pedidos-hielo
```
