#!/usr/bin/env bash
# Crea (o actualiza) toda la infraestructura de CI/CD con CloudFormation.
# Se ejecuta en AWS CloudShell, dentro de la carpeta del repositorio:
#   git clone https://github.com/LorenAlvare/api-pedidos-hielo.git
#   cd api-pedidos-hielo && bash scripts/desplegar.sh
set -euo pipefail

PILA="${PILA:-pedidos-hielo}"
REGION="${AWS_REGION:-us-east-1}"

echo "== Buscando la plataforma vigente de Elastic Beanstalk (Python 3.12, Amazon Linux 2023) =="
PLATAFORMA=$(aws elasticbeanstalk list-available-solution-stacks --region "$REGION" \
  --query "SolutionStacks[?contains(@, 'Amazon Linux 2023') && contains(@, 'Python 3.12')] | [0]" --output text)
if [ -z "$PLATAFORMA" ] || [ "$PLATAFORMA" = "None" ]; then
  echo "No se encontro la plataforma de Python 3.12 en $REGION." >&2; exit 1
fi
echo "   $PLATAFORMA"

if [ -z "${TOKEN_GITHUB:-}" ]; then
  read -r -s -p "Pega tu token personal de GitHub (no se muestra): " TOKEN_GITHUB; echo
fi

echo "== Desplegando la pila $PILA (tarda unos 10 minutos: crea dos entornos de Beanstalk) =="
aws cloudformation deploy --region "$REGION" \
  --stack-name "$PILA" \
  --template-file infra/pipeline.yml \
  --parameter-overrides \
    "PlataformaBeanstalk=$PLATAFORMA" \
    "TokenGitHub=$TOKEN_GITHUB" \
    "PropietarioGitHub=${PROPIETARIO_GITHUB:-LorenAlvare}" \
    "RepositorioGitHub=${REPOSITORIO_GITHUB:-api-pedidos-hielo}" \
    "Rama=${RAMA:-main}"

echo "== Listo. Salidas de la pila: =="
aws cloudformation describe-stacks --region "$REGION" --stack-name "$PILA" \
  --query "Stacks[0].Outputs[].[OutputKey,OutputValue]" --output table
