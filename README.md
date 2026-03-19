# Feirinha Notion Bot

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![AWS Lambda](https://img.shields.io/badge/AWS-Lambda-FF9900?logo=awslambda&logoColor=white)
![AWS SAM](https://img.shields.io/badge/AWS-SAM-0B5CAB?logo=amazonaws&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?logo=telegram&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--5%20mini-412991?logo=openai&logoColor=white)
![Notion](https://img.shields.io/badge/Notion-API-000000?logo=notion&logoColor=white)
![DynamoDB](https://img.shields.io/badge/AWS-DynamoDB-4053D6?logo=amazondynamodb&logoColor=white)

Bot Telegram serverless que automatiza o cadastro de compras de supermercado no Notion. Basta enviar uma foto do comprovante com a forma de pagamento na legenda e a IA extrai e cadastra todos os produtos automaticamente.

## Demonstração

[![Demonstração do Bot](/assets/demo.png)](https://youtube.com/shorts/bw33TnZIlac)

## Funcionalidades

- 📸 Envie foto do comprovante via Telegram com a forma de pagamento na legenda
- 🤖 IA (OpenAI GPT-5 mini) extrai dados estruturados
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
git clone <repo>
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
- **Qnt.** (Number): Quantidade
- **Valor** (Number): Preço em Reais
- **Desconto** (Number): Desconto aplicado
- **Pago** (Formula): `prop("Valor") - prop("Desconto")`
- **Categoria** (Select): Extra, Básico, Óleos/condimentos, Padaria, Bebidas, Carnes/ovos, Frios, Lanches/besteiras, Temperos, Grãos/mel, Frutas, Legumes/verduras, Limpeza, Higiene
- **Forma de Pagamento** (Select): Espécie, Pix, Débito - Inter, Crédito - Inter, Débito - Nubank, Crédito - Nubank

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
- **Parameter AuthorizedUserIds**: Um ou mais Telegram User IDs separados por vírgula
- **Parameter OpenAIApiKey**: Chave da API OpenAI
- **Parameter NotionConfigByUser**: JSON com `database_id` e `token` por usuário
- **Confirm changes before deploy**: Y
- **Allow SAM CLI IAM role creation**: Y
- **Disable rollback**: N
- **Save arguments to samconfig.toml**: Y

Exemplo de `NotionConfigByUser`:

```json
{
  "123456789": {
    "database_id": "sua_database_id",
    "token": "secret_xxx"
  }
}
```

### 3. Configure o Webhook do Telegram

Após o deploy, a URL do webhook será exibida nos outputs. Configure:

**Opção 1: script helper**
```bash
./scripts/setup-webhook.sh <BOT_TOKEN> <WEBHOOK_URL> <SECRET_TOKEN>
```

**Opção 2: manualmente**
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
│   ├── domain/
│   │   └── product.py              # Tipo estruturado de produto validado
│   ├── services/
│   │   └── receipt_processing_service.py  # Orquestra o fluxo principal da nota
│   ├── telegram/
│   │   ├── handler.py              # Processa mensagens do Telegram
│   │   └── security.py             # Validação de segurança
│   ├── processing/
│   │   ├── openai_client.py        # Integração com OpenAI
│   │   └── receipt_parser.py       # Parser e validação de dados
│   ├── notion/
│   │   ├── client.py               # Cliente Notion API
│   │   └── schema.py               # Schema e serialização da base Notion
│   └── storage/
│       └── dynamodb_client.py      # Deduplicação de updates
├── tests/
│   ├── processing/
│   │   └── test_receipt_parser.py
│   ├── notion/
│   │   └── test_client.py
│   └── test_lambda_handler.py
├── template.yaml                   # Infraestrutura AWS SAM
├── requirements.txt                # Dependências Python
└── README.md                       # Este arquivo
```

## Custos Estimados

Para uso pessoal (5-10 notas/mês):
- **AWS Lambda**: Gratuito (dentro do free tier)
- **API Gateway**: Gratuito (dentro do free tier)
- **OpenAI**: custo variável por imagem (GPT-5 mini)
- **Total**: < $1/mês

## Segurança

O bot implementa 3 camadas de segurança:

1. **Secret Token**: Valida que requests vêm do Telegram
2. **User ID Whitelist**: Apenas usuários autorizados
3. **Environment Variables**: Credenciais isoladas

## Troubleshooting

### Rodar testes unitários

```bash
python3 -m unittest discover -s tests -p 'test*.py'
```

### Ver logs da Lambda

```bash
sam logs --stack-name feirinha-notion-bot -n TelegramBotFunction --tail
```

### Testar localmente

```bash
# Exporte as variáveis de ambiente necessárias ou carregue-as no seu shell
sam local invoke TelegramBotFunction -e event.example.json
```

### Verificar webhook

```bash
curl "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"
```

### Remover webhook (para debug)

```bash
./scripts/delete-webhook.sh <BOT_TOKEN>
```

### Bot não responde

1. Verifique se o webhook está configurado: `curl "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"`
2. Verifique os logs da Lambda: `sam logs --stack-name feirinha-notion-bot -n TelegramBotFunction --tail`
3. Teste a função diretamente com `sam local invoke`

### Erro "User not authorized"

- Verifique se o `AuthorizedUserIds` está correto
- Use [@userinfobot](https://t.me/userinfobot) para confirmar seu User ID

### Erro de forma de pagamento inválida

- Envie novamente a foto com a forma de pagamento na legenda
- Valores aceitos: `Espécie`, `Pix`, `Débito - Inter`, `Crédito - Inter`, `Débito - Nubank`, `Crédito - Nubank`

### Erro ao processar imagem

- Verifique se há créditos na conta OpenAI
- Verifique os logs da Lambda para detalhes do erro

### Erro ao inserir no Notion

- Verifique se a integração está conectada à base
- Confirme que o schema da base está correto
- Verifique os nomes exatos das propriedades: `Produto`, `Data`, `Categoria`, `Tipo`, `Qnt.`, `Valor`, `Desconto`, `Forma de Pagamento`

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
