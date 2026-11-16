#!/usr/bin/env bash
# Usado por GitHub Actions. Despliega una version ya creada en un entorno de Beanstalk,
# espera a que termine (hasta 20 minutos) y comprueba que /health responda.
#   bash scripts/desplegar_version.sh <entorno> <version>
set -euo pipefail
ENTORNO="$1"; VERSION="$2"
INICIO=$(date -u +%Y-%m-%dT%H:%M:%SZ)

eventos() {
  echo "== Eventos de Beanstalk en $ENTORNO desde $INICIO =="
  aws elasticbeanstalk describe-events --environment-name "$ENTORNO" --start-time "$INICIO" \
    --query "reverse(Events)[].[EventDate,Severity,Message]" --output text || true
}

estado() {
  aws elasticbeanstalk describe-environments --environment-names "$ENTORNO" \
    --query "Environments[0].[Status,Health,VersionLabel,CNAME]" --output text
}

# Si el entorno esta ocupado (por ejemplo, un despliegue anterior), esperar a que quede listo
for i in $(seq 1 60); do
  read -r STATUS _ _ _ < <(estado)
  [ "$STATUS" = "Ready" ] && break
  echo "   Entorno $ENTORNO en estado $STATUS, esperando..."; sleep 20
done

echo "== Desplegando $VERSION en $ENTORNO =="
aws elasticbeanstalk update-environment --environment-name "$ENTORNO" --version-label "$VERSION" >/dev/null

for i in $(seq 1 60); do        # 60 x 20 s = 20 minutos
  sleep 20
  read -r STATUS SALUD ACTUAL URL < <(estado)
  echo "   [$(date -u +%H:%M:%S)] Estado: $STATUS | Salud: $SALUD | Version: $ACTUAL"
  [ "$STATUS" = "Ready" ] && break
done

eventos
if [ "$STATUS" != "Ready" ]; then
  echo "El entorno no termino de actualizarse en 20 minutos." >&2; exit 1
fi
if [ "$ACTUAL" != "$VERSION" ]; then
  echo "Beanstalk no dejo activa la version $VERSION (activa: $ACTUAL). Revisa los eventos de arriba." >&2; exit 1
fi

echo "== Comprobando http://$URL/health =="
for i in $(seq 1 12); do
  if curl -fsS "http://$URL/health"; then echo; echo "url=http://$URL" >> "${GITHUB_OUTPUT:-/dev/null}"; exit 0; fi
  sleep 10
done
echo "La API no respondio en /health" >&2; exit 1
