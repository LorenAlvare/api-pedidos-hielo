#!/usr/bin/env bash
# Usado por GitHub Actions. Despliega una version ya creada en un entorno de Beanstalk,
# espera a que termine y comprueba que /health responda.
#   bash scripts/desplegar_version.sh <entorno> <version>
set -euo pipefail
ENTORNO="$1"; VERSION="$2"

echo "== Desplegando $VERSION en $ENTORNO =="
aws elasticbeanstalk update-environment --environment-name "$ENTORNO" --version-label "$VERSION" >/dev/null
aws elasticbeanstalk wait environment-updated --environment-names "$ENTORNO"

read -r SALUD ACTUAL URL < <(aws elasticbeanstalk describe-environments --environment-names "$ENTORNO" \
  --query "Environments[0].[Health,VersionLabel,CNAME]" --output text)
echo "   Salud: $SALUD | Version activa: $ACTUAL | URL: http://$URL"
[ "$ACTUAL" = "$VERSION" ] || { echo "La version activa no es la esperada" >&2; exit 1; }

echo "== Comprobando http://$URL/health =="
for i in $(seq 1 12); do
  if curl -fsS "http://$URL/health"; then echo; echo "url=http://$URL" >> "${GITHUB_OUTPUT:-/dev/null}"; exit 0; fi
  sleep 10
done
echo "La API no respondio en /health" >&2; exit 1
