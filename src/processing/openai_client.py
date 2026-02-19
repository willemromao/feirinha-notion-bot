"""
Cliente para integração com OpenAI API
"""
import os
import logging
import base64
from typing import Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é um assistente de extração de dados de notas fiscais brasileiras.
Extraia TODOS os produtos da imagem com estas informações:

Campos obrigatórios:
- Data: Data da compra (formato: YYYY-MM-DD)
- Produto: Nome do produto
- Tipo: Descrição da embalagem (ex: "Vidro de 330 ml", "No peso - 300 g")
- Qnt: Quantidade (número de itens)
- Valor: Preço unitário ou total em Reais (apenas número, ex: 15.50)
- Desconto: Valor do desconto (0 se nenhum)
- Categoria: Escolha uma das categorias exatas: Extra, Básico, Óleos/condimentos, Padaria, Bebidas, Carnes/ovos, Frios, Lanches/besteiras, Temperos, Grãos/mel, Frutas, Legumes/verduras, Limpeza, Higiene
- Forma de Pagamento: Extraia do comprovante. Opções exatas: Will, Espécie, Pix, Débito - Inter, Crédito - Inter, Débito - Nubank, Crédito - Nubank

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
    "FormaDePagamento": "Pix"
  }
]

IMPORTANTE: Retorne APENAS o array JSON, sem texto adicional."""


class OpenAIClient:
    """Cliente para processar imagens com OpenAI Vision API"""

    def __init__(self):
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY não configurada")
        self.client = OpenAI(api_key=api_key)

    def extract_receipt_data(self, image_bytes: bytes) -> Optional[str]:
        """
        Processa imagem do comprovante e extrai dados estruturados

        Args:
            image_bytes: Bytes da imagem do comprovante

        Returns:
            String JSON com array de produtos ou None em caso de erro
        """
        try:
            # Codifica imagem em base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')

            logger.info("Enviando imagem para OpenAI...")

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            },
                            {
                                "type": "text",
                                "text": "Extraia todos os produtos desta nota fiscal e retorne o JSON conforme instruído."
                            }
                        ]
                    }
                ],
                max_tokens=2000,
                temperature=0.2
            )

            result = response.choices[0].message.content
            logger.info("Dados extraídos com sucesso da OpenAI")
            logger.debug(f"Resposta OpenAI: {result}")

            return result

        except Exception as e:
            logger.error(f"Erro ao processar imagem com OpenAI: {e}")
            return None
