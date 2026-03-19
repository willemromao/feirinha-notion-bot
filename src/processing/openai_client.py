"""
Cliente para integração com OpenAI API
"""
import os
import logging
import base64
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você extrai dados de notas fiscais brasileiras e responde apenas com JSON válido.

Objetivo:
- Extraia TODOS os produtos legíveis da imagem.
- Se houver muitos itens, priorize completude.
- Nunca retorne array vazio se houver ao menos um item legível.

Campos por produto:
- Data: data da compra no formato YYYY-MM-DD
- Produto: nome completo e natural do produto, sem abreviações desnecessárias e sem peso/volume/unidade
- Tipo: descrição da embalagem, peso, volume ou unidade em texto descritivo
- Qnt: quantidade numérica de itens
- Valor: valor numérico em reais, sem símbolo, usando ponto decimal se necessário
- Desconto: valor numérico do desconto; use 0 quando não houver desconto claro
- Categoria: escolha exatamente uma entre Extra, Básico, Óleos/condimentos, Padaria, Bebidas, Carnes/ovos, Frios, Lanches/besteiras, Temperos, Grãos/mel, Frutas, Legumes/verduras, Limpeza, Higiene
- Emoji: exatamente 1 emoji simples que represente bem o produto

Regras obrigatórias:
- Retorne APENAS um array JSON. Não escreva explicações, títulos, comentários ou markdown.
- Não use blocos de código.
- Não omita campos.
- Nunca inclua peso, volume ou unidade no campo Produto.
- Sempre coloque peso, volume ou unidade no campo Tipo em formato descritivo.
- Nunca retorne Tipo apenas como "KG", "G", "ML", "L", "UN", "PC" ou similares.
- Se não conseguir inferir o Tipo com segurança, retorne "".
- Preserve palavras inteiras no Produto.
- Corrija abreviações e truncamentos comuns do cupom para português natural.

Normalizações importantes:
- "Bisc Rech Amori Richester" -> "Biscoito Recheado Amori Richester"
- "Massa Sem Vitarella Parafuso" -> "Macarrão de Sêmola Vitarella Parafuso"
- "Leite Uht Piracijuba Int" -> "Leite UHT Piracanjuba Integral"
- Quando o texto do cupom indicar "massa sem..." de macarrão, normalize como "Macarrão de Sêmola ..."
- Quando o nome do produto for "CR LEITE UHT CCGL", normalize como "Creme de Leite CCGL"; aplique a mesma lógica para outras marcas de creme de leite
- Quando o nome do produto for "DUETO FUGINI", normalize como "Dueto Fugini" e não como macarrão; aplique a mesma lógica para outras marcas de dueto

Ajuda para categorias:
- Grãos/mel: granola, castanha, aveia, amendoim, mel, chia, linhaça
- Básico: arroz, feijão, açúcar, farinha, goma de tapioca, macarrão, sal, flocão de milho
- Óleos/condimentos: óleo, azeite, vinagre, maionese, molho de tomate, creme de leite, dueto, fermento
- Padaria: pão, bolo, coxinha, pastel, pão de queijo, farinha de rosca
- Bebidas: leite em pó, achocolatado, café, água, danone, leite em caixa
- Carnes/ovos: carne bovina, frango, peixe, ovos, linguiça, salsicha, sardinha
- Legumes/verduras: tomate, cebola, alface, batata, cenoura
- Temperos: pimenta, alho, coentro, pimentão, açafrão, orégano

Formato de saída:
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
]"""


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
