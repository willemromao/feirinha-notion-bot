"""
Cliente para integração com OpenAI API
"""
import os
import logging
import base64
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é um assistente de extração de dados de notas fiscais brasileiras.
Extraia TODOS os produtos da imagem com estas informações:

Campos obrigatórios:
- Data: Data da compra (formato: YYYY-MM-DD)
- Produto: Nome COMPLETO do produto, sem abreviar palavras e sem unidade/peso/volume
- Tipo: Descrição da embalagem/peso/volume (ex: "Pacote de 500 g", "No peso - 300 g")
- Qnt: Quantidade (número de itens)
- Valor: Preço unitário ou total em Reais (apenas número, ex: 15.50)
- Desconto: Valor do desconto (0 se nenhum)
- Categoria: Escolha uma das categorias exatas: Extra, Básico, Óleos/condimentos, Padaria, Bebidas, Carnes/ovos, Frios, Lanches/besteiras, Temperos, Grãos/mel, Frutas, Legumes/verduras, Limpeza, Higiene
- Emoji: Escolha exatamente 1 emoji que represente bem o produto

Regras obrigatórias de formatação:
- Nunca inclua peso/volume/unidade no campo Produto (ex: remover "480G", "1L", "KG", "UN", "PC")
- Sempre coloque peso/volume/unidade no campo Tipo em texto descritivo
- Nunca retorne Tipo apenas como "KG", "G", "ML", "L", "UN" ou similares
- Se não conseguir inferir o Tipo com segurança, retorne uma string vazia em vez de omitir o campo
- Se não houver desconto claro, retorne Desconto como 0
- Retorne exatamente 1 emoji simples no campo Emoji
- Preserve palavras inteiras no Produto (evite abreviações como "Bisc", "Mussarela Molfino Importad")
- Corrija abreviações e truncamentos comuns do cupom fiscal para português natural no Produto
- Quando o texto do cupom indicar "massa sem..." de macarrão, normalize como "Macarrão de Sêmola ..."
- Em notas com muitos produtos, priorize retornar todos os itens com campos completos; nunca retorne array vazio se houver itens legíveis

Exemplos de normalização esperada:
- "Bisc Rech Amori Richester" -> "Biscoito Recheado Amori Richester"
- "Massa Sem Vitarella Parafuso" -> "Macarrão de Sêmola Vitarella Parafuso"
- "Leite Uht Piracijuba Int" -> "Leite UHT Piracanjuba Integral"

Retorne um array JSON com todos os produtos no formato:
[
  {
    "Data": "YYYY-MM-DD",
    "Produto": "Nome do produto",
    "Tipo": "Descrição da embalagem",
    "Qnt": 1,
    "Valor": 10.50,
    "Desconto": 0,
    "Categoria": "Básico",
    "Emoji": "🥛"
  }
]

IMPORTANTE: Retorne APENAS o array JSON, sem texto adicional."""


class OpenAIClient:
    """Cliente para processar imagens com OpenAI Vision API"""

    def __init__(self):
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY não configurada")
        self.api_key = api_key

    def extract_receipt_data(self, image_bytes: bytes) -> Optional[str]:
        """
        Processa imagem do comprovante e extrai dados estruturados

        Args:
            image_bytes: Bytes da imagem do comprovante

        Returns:
            String JSON com array de produtos ou None em caso de erro
        """
        try:
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')

            logger.info("Enviando imagem para OpenAI...")

            payload = {
                "model": "gpt-5-mini",
                "instructions": SYSTEM_PROMPT,
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": "Extraia todos os produtos desta nota fiscal e retorne o JSON conforme instruído."
                            },
                            {
                                "type": "input_image",
                                "image_url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        ]
                    }
                ],
                "reasoning": {
                    "effort": "low",
                }
            }

            try:
                response = httpx.post(
                    "https://api.openai.com/v1/responses",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=120.0
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                body = exc.response.text if exc.response is not None else "<sem resposta>"
                logger.error(f"OpenAI retornou HTTP {exc.response.status_code if exc.response else '??'}: {body}")
                return None

            response_json = response.json()

            result = response_json.get("output_text")
            if not result:
                output = response_json.get("output", [])
                texts = []
                for item in output:
                    for content in item.get("content", []):
                        if content.get("type") in {"output_text", "text"} and content.get("text"):
                            texts.append(content["text"])
                result = "\n".join(texts).strip()

            if not result:
                logger.error(f"Resposta sem texto útil da OpenAI: {response_json}")
                return None

            logger.info("Dados extraídos com sucesso da OpenAI")

            return result

        except Exception as e:
            logger.error(f"Erro ao processar imagem com OpenAI: {e}")
            return None
