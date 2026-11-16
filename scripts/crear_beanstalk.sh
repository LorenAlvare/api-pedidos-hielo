#!/usr/bin/env bash
# Crea la aplicacion y los entornos de Elastic Beanstalk (pruebas y produccion) con CloudFormation.
# Se ejecuta UNA vez en AWS CloudShell, dentro de la carpeta del repositorio:
#   bash scripts/crear_beanstalk.sh
# Despues, GitHub Actions despliega solo en cada push a main.
set -euo pipefail

PILA="${PILA:-pedidos-hielo-beanstalk}"
REGION="${AWS_REGION:-us-east-1}"

ESTADO=$(aws cloudformation describe-stacks --region "$REGION" --stack-name "$PILA" \
  --query "Stacks[0].StackStatus" --output text 2>/dev/null || echo NO_EXISTE)
if [ "$ESTADO" = "ROLLBACK_COMPLETE" ] || [ "$ESTADO" = "ROLLBACK_FAILED" ]; then
  echo "== Borrando la pila fallida anterior ($ESTADO) =="
  aws cloudformation delete-stack --region "$REGION" --stack-name "$PILA"
fi
# Borra tambien la pila del intento con CodePipeline, si quedo fallida
for vieja in "$PILA" pedidos-hielo; do
  E=$(aws cloudformation describe-stacks --region "$REGION" --stack-name "$vieja" \
    --query "Stacks[0].StackStatus" --output text 2>/dev/null || echo NO_EXISTE)
  if [ "$vieja" = pedidos-hielo ] && [ "$E" = "ROLLBACK_COMPLETE" ]; then
    aws cloudformation delete-stack --region "$REGION" --stack-name "$vieja"; E=DELETE_IN_PROGRESS
  fi
  if [ "$E" = "DELETE_IN_PROGRESS" ]; then
    echo "== Esperando a que termine de borrarse la pila $vieja =="
    aws cloudformation wait stack-delete-complete --region "$REGION" --stack-name "$vieja"
  fi
done

echo "== Buscando la plataforma vigente de Elastic Beanstalk (Python 3.12, Amazon Linux 2023) =="
PLATAFORMA=$(aws elasticbeanstalk list-available-solution-stacks --region "$REGION" \
  --query "SolutionStacks[?contains(@, 'Amazon Linux 2023') && contains(@, 'Python 3.12')] | [0]" --output text)
echo "   $PLATAFORMA"

echo "== Creando la pila $PILA (tarda unos 10 minutos: crea dos entornos de Beanstalk) =="
if ! aws cloudformation deploy --region "$REGION" --stack-name "$PILA" \
  --template-file infra/beanstalk.yml \
  --parameter-overrides "PlataformaBeanstalk=$PLATAFORMA"; then
  echo "== Fallo. Motivo segun CloudFormation: ==" >&2
  aws cloudformation describe-stack-events --region "$REGION" --stack-name "$PILA" \
    --query "StackEvents[?contains(ResourceStatus,'FAILED')].[LogicalResourceId,ResourceStatusReason]" --output text >&2
  exit 1
fi

echo "== Listo. URLs: =="
aws cloudformation describe-stacks --region "$REGION" --stack-name "$PILA" \
  --query "Stacks[0].Outputs[].[OutputKey,OutputValue]" --output table
