# Guía: CI/CD de la API de Pedidos de Hielo en AWS

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

## 0. Antes de empezar

- **AWS Academy Learner Lab**: inicia el laboratorio ("Start Lab") y entra a la consola. La plantilla usa
  `LabRole` y `LabInstanceProfile`, que ya existen en el laboratorio. Trabaja en la región **us-east-1**.
- **CodeCommit no se usa**: AWS cerró CodeCommit a cuentas nuevas, por eso la fuente es GitHub.

## 1. Crear un token de GitHub

1. GitHub → foto de perfil → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**.
2. **Generate new token (classic)**, nombre `codepipeline`, marca el permiso **repo** y genéralo.
3. Copia el token (empieza por `ghp_`). Solo se muestra una vez.

## 2. Desplegar la infraestructura (CloudShell)

En la consola de AWS abre **CloudShell** (ícono `>_` arriba) y ejecuta:

```bash
git clone https://github.com/LorenAlvare/api-pedidos-hielo.git
cd api-pedidos-hielo
bash scripts/desplegar.sh
```

El script busca solo la versión vigente de la plataforma de Beanstalk (Python 3.12), te pide el token
y crea la pila `pedidos-hielo`. Tarda unos 10 minutos. Al final muestra las URL de pruebas y producción.

> Alternativa sin CloudShell: **CloudFormation → Crear pila → Cargar un archivo de plantilla** →
> `infra/pipeline.yml`. Llena `TokenGitHub` y `PlataformaBeanstalk` (el nombre exacto sale de
> `aws elasticbeanstalk list-available-solution-stacks`).

## 3. Ver el pipeline en acción

1. **CodePipeline → pedidos-hielo-pipeline**. La primera ejecución arranca sola al crearse.
2. **Construcción** abre CodeBuild: pestaña *Registros de compilación* (salida de pytest) e *Informes*
   (resultado de las pruebas en formato JUnit).
3. Cuando **DesplegarPruebas** termina, abre la URL de pruebas + `/docs` para probar la API.
4. En **Aprobación** pulsa *Revisar* → *Aprobar*. Se despliega a producción.

## 4. Demostrar el despliegue automático (para el video)

1. Haz un cambio visible, por ejemplo la versión en `app/main.py` (`version="1.1.0"`), y súbelo:
   ```bash
   git commit -am "Subir versión a 1.1.0" && git push
   ```
2. En 1-2 minutos el pipeline arranca solo con ese commit (se ve el mensaje del commit en la etapa Fuente).
3. Muestra CodeBuild corriendo las pruebas, el despliegue a pruebas, la aprobación y producción.
4. Abre `URL/` y muestra que la versión cambió.
5. Extra: sube un cambio que rompa una prueba y muestra que el pipeline se detiene en Construcción
   y no llega a desplegarse. Luego reviértelo.

## 5. Capturas sugeridas para el informe PDF

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

## Problemas comunes

| Error | Solución |
|-------|----------|
| `Cannot have more than 0 builds in queue` | Límite de CodeBuild de cuentas nuevas. Pide aumento en *Service Quotas* o abre un caso de soporte; en Learner Lab reinicia el lab y prueba de nuevo. |
| La etapa Fuente falla con el token | Revisa que el token tenga permiso `repo` y no haya vencido. Si sigue fallando, crea una conexión en **Developer Tools → Settings → Connections → GitHub**, autorízala y vuelve a desplegar con `ArnConexion=<arn>` en vez del token. |
| `No Solution Stack named ...` | La versión de la plataforma cambió. Usa `scripts/desplegar.sh`, que la busca sola. |
| Beanstalk en rojo (*Severe*) | Revisa *Registros* del entorno. La app arranca con el `Procfile` (`uvicorn` en el puerto 8000) y el chequeo de salud es `/health`. |
| El laboratorio se cerró | Al reiniciar Learner Lab, la pila sigue; si los entornos quedaron detenidos, vuelve a ejecutar el pipeline con *Liberar cambio*. |

## Borrar todo al terminar

```bash
aws s3 rm s3://$(aws cloudformation describe-stack-resource --stack-name pedidos-hielo \
  --logical-resource-id BucketArtefactos --query StackResourceDetail.PhysicalResourceId --output text) --recursive
aws cloudformation delete-stack --stack-name pedidos-hielo
```
