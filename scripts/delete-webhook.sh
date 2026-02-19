#!/bin/bash

# Script para remover webhook do Telegram
# Uso: ./scripts/delete-webhook.sh <BOT_TOKEN>

if [ "$#" -ne 1 ]; then
    echo "Uso: $0 <BOT_TOKEN>"
    echo ""
    echo "Exemplo:"
    echo "  $0 123456:ABC-DEF..."
    exit 1
fi

BOT_TOKEN=$1

echo "Removendo webhook do Telegram..."

RESPONSE=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/deleteWebhook")

echo "Resposta:"
echo "$RESPONSE" | python3 -m json.tool

echo ""
echo "Verificando configuração do webhook..."
curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo" | python3 -m json.tool
