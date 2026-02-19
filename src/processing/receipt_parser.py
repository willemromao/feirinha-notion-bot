"""
Parser para processar e validar dados extraídos de comprovantes
"""
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

VALID_CATEGORIES = [
    "Extra", "Básico", "Óleos/condimentos", "Padaria", "Bebidas",
    "Carnes/ovos", "Frios", "Lanches/besteiras", "Temperos",
    "Grãos/mel", "Frutas", "Legumes/verduras", "Limpeza", "Higiene"
]

VALID_PAYMENT_METHODS = [
    "Will", "Espécie", "Pix", "Débito - Inter", "Crédito - Inter",
    "Débito - Nubank", "Crédito - Nubank"
]


class ReceiptParser:
    """Parser para validar e estruturar dados de comprovantes"""

    @staticmethod
    def parse_openai_response(response: str) -> Optional[List[Dict[str, Any]]]:
        """
        Faz parse da resposta JSON da OpenAI e valida os dados

        Args:
            response: String JSON retornada pela OpenAI

        Returns:
            Lista de produtos validados ou None em caso de erro
        """
        try:
            # Remove possíveis marcadores markdown
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()

            # Parse JSON
            products = json.loads(cleaned_response)

            if not isinstance(products, list):
                logger.error("Resposta da OpenAI não é um array")
                return None

            # Valida cada produto
            validated_products = []
            for idx, product in enumerate(products):
                validated = ReceiptParser._validate_product(product, idx)
                if validated:
                    validated_products.append(validated)

            if not validated_products:
                logger.error("Nenhum produto válido encontrado")
                return None

            logger.info(f"{len(validated_products)} produtos validados com sucesso")
            return validated_products

        except json.JSONDecodeError as e:
            logger.error(f"Erro ao fazer parse do JSON: {e}")
            logger.error(f"Resposta recebida: {response}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao processar resposta: {e}")
            return None

    @staticmethod
    def _validate_product(product: Dict[str, Any], index: int) -> Optional[Dict[str, Any]]:
        """
        Valida campos individuais de um produto

        Args:
            product: Dicionário com dados do produto
            index: Índice do produto na lista

        Returns:
            Produto validado ou None se inválido
        """
        try:
            # Campos obrigatórios
            required_fields = ["Data", "Produto", "Tipo", "Qnt", "Valor", "Desconto", "Categoria", "FormaDePagamento"]
            for field in required_fields:
                if field not in product:
                    logger.warning(f"Produto {index}: campo '{field}' ausente")
                    return None

            # Valida categoria
            categoria = product["Categoria"]
            if categoria not in VALID_CATEGORIES:
                logger.warning(f"Produto {index}: categoria inválida '{categoria}'")
                # Tenta mapear para categoria válida (fallback)
                categoria = "Extra"

            # Valida forma de pagamento
            forma_pagamento = product["FormaDePagamento"]
            if forma_pagamento not in VALID_PAYMENT_METHODS:
                logger.warning(f"Produto {index}: forma de pagamento inválida '{forma_pagamento}'")
                # Fallback para Pix
                forma_pagamento = "Pix"

            # Valida tipos numéricos
            qnt = float(product["Qnt"])
            valor = float(product["Valor"])
            desconto = float(product.get("Desconto", 0))

            # Monta produto validado
            validated = {
                "Data": product["Data"],
                "Produto": str(product["Produto"]),
                "Tipo": str(product["Tipo"]),
                "Qnt": qnt,
                "Valor": valor,
                "Desconto": desconto,
                "Categoria": categoria,
                "FormaDePagamento": forma_pagamento
            }

            return validated

        except (ValueError, TypeError) as e:
            logger.warning(f"Produto {index}: erro de validação - {e}")
            return None
