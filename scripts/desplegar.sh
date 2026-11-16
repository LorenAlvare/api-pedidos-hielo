#!/usr/bin/env bash
# Crea (o actualiza) toda la infraestructura de CI/CD con CloudFormation.
# Se ejecuta en AWS CloudShell, dentro de la carpeta del repositorio:
#   git clone https://github.com/LorenAlvare/api-pedidos-hielo.git
#   cd api-pedidos-hielo && bash scripts/desplegar.sh
#
# Modo de pruebas (variable MODO_PRUEBAS):
#   CodeBuild (por defecto) - proyecto de CodeBuild con buildspec.yml
#   Commands                - accion Commands de CodePipeline (no crea proyecto de CodeBuild)
#   Ninguno                 - CodePipeline solo despliega; las pruebas quedan en GitHub Actions
# Ejemplo: MODO_PRUEBAS=Commands bash scripts/desplegar.sh
set -euo pipefail

PILA="${PILA:-pedidos-hielo}"
REGION="${AWS_REGION:-us-east-1}"
MODO="${MODO_PRUEBAS:-CodeBuild}"

# Si un intento anterior fallo al crear la pila, hay que borrarla antes de reintentar
ESTADO=$(aws cloudformation describe-stacks --region "$REGION" --stack-name "$PILA" \
  --query "Stacks[0].StackStatus" --output text 2>/dev/null || echo NO_EXISTE)
if [ "$ESTADO" = "ROLLBACK_COMPLETE" ] || [ "$ESTADO" = "ROLLBACK_FAILED" ]; then
  echo "== Borrando la pila fallida anterior ($ESTADO) =="
  aws cloudformation delete-stack --region "$REGION" --stack-name "$PILA"
  aws cloudformation wait stack-delete-complete --region "$REGION" --stack-name "$PILA"
elif [ "$ESTADO" = "DELETE_IN_PROGRESS" ]; then
  echo "== Esperando a que termine de borrarse la pila anterior =="
  aws cloudformation wait stack-delete-complete --region "$REGION" --stack-name "$PILA"
fi

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

echo "== Desplegando la pila $PILA, modo de pruebas $MODO (tarda unos 10 minutos: crea dos entornos de Beanstalk) =="
if ! aws cloudformation deploy --region "$REGION" \
  --stack-name "$PILA" \
  --template-file infra/pipeline.yml \
  --parameter-overrides \
    "PlataformaBeanstalk=$PLATAFORMA" \
    "ModoPruebas=$MODO" \
    "TokenGitHub=$TOKEN_GITHUB" \
    "PropietarioGitHub=${PROPIETARIO_GITHUB:-LorenAlvare}" \
    "RepositorioGitHub=${REPOSITORIO_GITHUB:-api-pedidos-hielo}" \
    "Rama=${RAMA:-main}"; then
  echo "== Fallo. Motivo segun CloudFormation: ==" >&2
  aws cloudformation describe-stack-events --region "$REGION" --stack-name "$PILA" \
    --query "StackEvents[?contains(ResourceStatus,'FAILED')].[LogicalResourceId,ResourceStatusReason]" --output text >&2
  exit 1
fi

echo "== Listo. Salidas de la pila: =="
aws cloudformation describe-stacks --region "$REGION" --stack-name "$PILA" \
  --query "Stacks[0].Outputs[].[OutputKey,OutputValue]" --output table
