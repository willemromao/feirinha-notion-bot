#!/bin/bash

# Script para configurar webhook do Telegram
# Uso: ./scripts/setup-webhook.sh <BOT_TOKEN> <WEBHOOK_URL> <SECRET_TOKEN>

if [ "$#" -ne 3 ]; then
    echo "Uso: $0 <BOT_TOKEN> <WEBHOOK_URL> <SECRET_TOKEN>"
    echo ""
    echo "Exemplo:"
    echo "  $0 123456:ABC-DEF... https://xyz.execute-api.us-east-1.amazonaws.com/webhook my-secret-token"
    exit 1
fi

BOT_TOKEN=$1
WEBHOOK_URL=$2
SECRET_TOKEN=$3

echo "Configurando webhook do Telegram..."
echo "URL: $WEBHOOK_URL"

RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"${WEBHOOK_URL}\", \"secret_token\": \"${SECRET_TOKEN}\"}")

echo ""
echo "Resposta:"
echo "$RESPONSE" | python3 -m json.tool

echo ""
echo "Verificando configuração do webhook..."
curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo" | python3 -m json.tool
