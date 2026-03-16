# Bot Telegram - Cadastro Automático de Compras no Notion

Bot Telegram serverless que automatiza o cadastro de compras de supermercado no Notion. Basta enviar uma foto do comprovante com a forma de pagamento na legenda e a IA extrai e cadastra todos os produtos automaticamente.

## Funcionalidades

- 📸 Envie foto do comprovante via Telegram com a forma de pagamento na legenda
- 🤖 IA (OpenAI GPT-4o-mini) extrai dados estruturados
- 📊 Cadastro automático no Notion
- 🔒 Segurança com validação de usuário autorizado
- ☁️ Arquitetura serverless AWS (sem servidor 24h)

## Arquitetura

```
Telegram → API Gateway → Lambda → [OpenAI + Notion]
```

## Pré-requisitos

1. **Conta AWS** com permissões para:
   - Lambda
   - API Gateway
   - CloudWatch Logs
   - IAM (para criar roles)

2. **AWS CLI** instalado e configurado
   ```bash
   aws configure
   ```

3. **AWS SAM CLI** instalado ([guia de instalação](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html))

4. **Python 3.12** instalado

5. **Contas e Tokens**:
   - Bot do Telegram (via [@BotFather](https://t.me/botfather))
   - Chave da API OpenAI
   - Token de integração do Notion
   - ID da base de dados Notion

## Setup

### 1. Clone o Repositório

```bash
git clone <seu-repo>
cd feirinha-notion-bot
```

### 2. Configure o Notion

1. Acesse [Notion Integrations](https://www.notion.so/my-integrations)
2. Crie uma nova integração e copie o token
3. Na sua base de dados Notion, clique em "..." → "Connect to" → Selecione sua integração
4. Copie o ID da base (está na URL: `https://notion.so/<workspace>/<DATABASE_ID>?v=...`)

**Schema da Base Notion:**
- **Data** (Date): Data da compra
- **Produto** (Title): Nome do produto
- **Tipo** (Text): Descrição da embalagem
- **Qnt** (Number): Quantidade
- **Valor** (Number): Preço em Reais
- **Desconto** (Number): Desconto aplicado
- **Pago** (Formula): `prop("Valor") - prop("Desconto")`
- **Categoria** (Select): Extra, Básico, Óleos/condimentos, Padaria, Bebidas, Carnes/ovos, Frios, Lanches/besteiras, Temperos, Grãos/mel, Frutas, Legumes/verduras, Limpeza, Higiene
- **Forma de Pagamento** (Select): Will, Espécie, Pix, Débito - Inter, Crédito - Inter, Débito - Nubank, Crédito - Nubank

### 3. Crie o Bot no Telegram

1. Fale com [@BotFather](https://t.me/botfather)
2. Use `/newbot` e siga as instruções
3. Copie o token fornecido
4. Para obter seu User ID, fale com [@userinfobot](https://t.me/userinfobot)

### 4. Gere um Secret Token

```bash
# Linux/Mac
openssl rand -hex 32

# Ou use qualquer string aleatória segura
```

## Deployment

### 1. Build do Projeto

```bash
sam build
```

### 2. Deploy Interativo (primeira vez)

```bash
sam deploy --guided
```

Será solicitado:
- **Stack Name**: `feirinha-notion-bot`
- **AWS Region**: `us-east-1` (ou sua preferência)
- **Parameter TelegramBotToken**: Token do BotFather
- **Parameter TelegramSecretToken**: Token secreto gerado
- **Parameter AuthorizedUserId**: Seu Telegram User ID
- **Parameter OpenAIApiKey**: Chave da API OpenAI
- **Parameter NotionToken**: Token de integração Notion
- **Parameter NotionDatabaseId**: ID da base Notion
- **Confirm changes before deploy**: Y
- **Allow SAM CLI IAM role creation**: Y
- **Disable rollback**: N
- **Save arguments to samconfig.toml**: Y

### 3. Configure o Webhook do Telegram

Após o deploy, a URL do webhook será exibida nos outputs. Configure:

```bash
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "<WEBHOOK_URL>",
    "secret_token": "<SECRET_TOKEN>"
  }'
```

Substitua:
- `<BOT_TOKEN>`: Seu token do Telegram
- `<WEBHOOK_URL>`: URL do output `WebhookUrl`
- `<SECRET_TOKEN>`: Token secreto usado no deploy

### 4. Teste o Bot

1. Abra o Telegram e busque seu bot
2. Envie uma foto de um comprovante de compra com a forma de pagamento na legenda
3. Exemplos de legenda: `Pix`, `Débito - Inter`, `credito nubank`, `pagamento: espécie`
4. Aguarde a confirmação
5. Verifique os produtos no Notion

## Deploys Subsequentes

Após configurar o `samconfig.toml`, basta:

```bash
sam build && sam deploy
```

## Estrutura do Projeto

```
feirinha-notion-bot/
├── src/
│   ├── lambda_handler.py           # Entry point da Lambda
│   ├── telegram/
│   │   ├── handler.py              # Processa mensagens do Telegram
│   │   └── security.py             # Validação de segurança
│   ├── processing/
│   │   ├── openai_client.py        # Integração com OpenAI
│   │   └── receipt_parser.py       # Parser e validação de dados
│   └── notion/
│       └── client.py               # Cliente Notion API
├── template.yaml                   # Infraestrutura AWS SAM
├── requirements.txt                # Dependências Python
└── README.md                       # Este arquivo
```

## Custos Estimados

Para uso pessoal (5-10 notas/mês):
- **AWS Lambda**: Gratuito (dentro do free tier)
- **API Gateway**: Gratuito (dentro do free tier)
- **OpenAI**: ~$0.01-0.05 por imagem (GPT-4o-mini)
- **Total**: < $5/mês

## Segurança

O bot implementa 3 camadas de segurança:

1. **Secret Token**: Valida que requests vêm do Telegram
2. **User ID Whitelist**: Apenas usuários autorizados
3. **Environment Variables**: Credenciais isoladas

## Troubleshooting

### Ver logs da Lambda

```bash
sam logs -n TelegramBotFunction --tail
```

### Testar localmente

```bash
# Crie um arquivo .env com as variáveis
cp .env.example .env
# Edite o .env com suas credenciais

# Execute teste local
sam local invoke TelegramBotFunction -e event.json
```

### Verificar webhook

```bash
curl "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"
```

### Remover webhook (para debug)

```bash
curl "https://api.telegram.org/bot<BOT_TOKEN>/deleteWebhook"
```

## Logs e Monitoramento

Os logs são automaticamente enviados para CloudWatch Logs. Acesse:
1. Console AWS → CloudWatch → Log Groups
2. Busque por `/aws/lambda/feirinha-notion-bot-TelegramBotFunction-*`

## Deletar a Stack

```bash
sam delete
```

## Licença

MIT License - Veja o arquivo LICENSE para detalhes.

## Suporte

Para problemas ou dúvidas, abra uma issue no GitHub.
