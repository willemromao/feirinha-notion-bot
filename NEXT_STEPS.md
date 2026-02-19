# Próximos Passos

Guia rápido para colocar o bot em produção.

## 1. Obter Credenciais

### Telegram Bot Token
1. Abra o Telegram e busque por [@BotFather](https://t.me/botfather)
2. Digite `/newbot` e siga as instruções
3. Copie o token fornecido (formato: `123456789:ABC-DEFghIJKlmNOpqrs`)
4. Para descobrir seu User ID, fale com [@userinfobot](https://t.me/userinfobot)

### OpenAI API Key
1. Acesse [platform.openai.com](https://platform.openai.com)
2. Vá em API Keys
3. Crie uma nova chave e copie
4. Adicione créditos na conta (mínimo $5)

### Notion Integration
1. Acesse [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Clique em "+ New integration"
3. Dê um nome (ex: "Telegram Bot")
4. Selecione o workspace
5. Copie o "Internal Integration Token"

### Notion Database ID
1. Abra sua base de dados no Notion
2. Clique em "..." no canto superior direito
3. Clique em "Connect to" e selecione sua integração
4. Copie o ID da URL: `https://notion.so/<workspace>/<DATABASE_ID>?v=...`
   - O DATABASE_ID é a parte entre o workspace e o `?v=`

### Secret Token
Gere um token aleatório seguro:
```bash
openssl rand -hex 32
```

## 2. Configurar AWS

### Instalar AWS CLI
```bash
# Linux/Mac
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verificar instalação
aws --version
```

### Configurar Credenciais
```bash
aws configure
```

Será solicitado:
- **AWS Access Key ID**: Sua chave de acesso
- **AWS Secret Access Key**: Sua chave secreta
- **Default region name**: `us-east-1` (ou sua preferência)
- **Default output format**: `json`

### Instalar SAM CLI
```bash
# Linux
wget https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-linux-x86_64.zip
unzip aws-sam-cli-linux-x86_64.zip -d sam-installation
sudo ./sam-installation/install

# Verificar instalação
sam --version
```

## 3. Deploy

### Build
```bash
sam build
```

### Deploy (primeira vez)
```bash
sam deploy --guided
```

Responda as perguntas:
- **Stack Name**: `feirinha-notion-bot`
- **AWS Region**: `us-east-1`
- **Parameter TelegramBotToken**: Cole o token do BotFather
- **Parameter TelegramSecretToken**: Cole o token gerado
- **Parameter AuthorizedUserId**: Cole seu User ID do Telegram
- **Parameter OpenAIApiKey**: Cole sua chave OpenAI
- **Parameter NotionToken**: Cole o token de integração Notion
- **Parameter NotionDatabaseId**: Cole o ID da base Notion
- **Confirm changes before deploy**: Y
- **Allow SAM CLI IAM role creation**: Y
- **Disable rollback**: N
- **Save arguments to samconfig.toml**: Y

### Copiar URL do Webhook
Após o deploy, copie a **WebhookUrl** exibida nos outputs.

## 4. Configurar Webhook

### Opção 1: Usando o script helper
```bash
./scripts/setup-webhook.sh <BOT_TOKEN> <WEBHOOK_URL> <SECRET_TOKEN>
```

### Opção 2: Manualmente
```bash
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "<WEBHOOK_URL>",
    "secret_token": "<SECRET_TOKEN>"
  }'
```

### Verificar webhook
```bash
curl "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"
```

Você deve ver `"url": "<WEBHOOK_URL>"` na resposta.

## 5. Testar

1. Abra o Telegram
2. Busque pelo nome do seu bot
3. Envie `/start` para iniciar a conversa
4. Tire uma foto de um comprovante de compra ou envie uma imagem
5. Aguarde a resposta do bot
6. Verifique os produtos no Notion

## 6. Monitorar

### Ver logs em tempo real
```bash
sam logs -n TelegramBotFunction --tail
```

### Ver logs no AWS Console
1. Acesse [console.aws.amazon.com/cloudwatch](https://console.aws.amazon.com/cloudwatch)
2. Clique em "Log groups" no menu lateral
3. Busque por `/aws/lambda/feirinha-notion-bot-TelegramBotFunction-*`
4. Clique no log group e depois em um log stream

## 7. Atualizar o Bot

Após fazer alterações no código:

```bash
sam build && sam deploy
```

O webhook não precisa ser reconfigurado.

## Troubleshooting

### Bot não responde
1. Verifique se o webhook está configurado: `curl "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"`
2. Verifique os logs da Lambda: `sam logs -n TelegramBotFunction --tail`
3. Teste a função Lambda diretamente no Console AWS

### Erro "User not authorized"
- Verifique se o `AuthorizedUserId` está correto
- Use [@userinfobot](https://t.me/userinfobot) para confirmar seu User ID

### Erro ao processar imagem
- Verifique se há créditos na conta OpenAI
- Verifique os logs da Lambda para detalhes do erro

### Erro ao inserir no Notion
- Verifique se a integração está conectada à base
- Confirme que o schema da base está correto
- Verifique os nomes exatos das propriedades (case-sensitive)

## Custos

Para uso pessoal (5-10 comprovantes/mês):
- **AWS**: Gratuito (free tier)
- **OpenAI**: ~$0.50/mês
- **Total**: < $1/mês

## Desinstalar

Para remover completamente o bot:

```bash
# Remover webhook
./scripts/delete-webhook.sh <BOT_TOKEN>

# Deletar stack AWS
sam delete
```
