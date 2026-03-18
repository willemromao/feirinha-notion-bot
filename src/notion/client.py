"""
Cliente para integração com Notion API
"""
import logging
from typing import List, Dict, Any
from notion_client import Client
from processing.receipt_parser import ReceiptParser

logger = logging.getLogger(__name__)
DEFAULT_PRODUCT_EMOJI = "🛒"

class NotionClient:
    """Cliente para inserir produtos na base Notion"""

    def __init__(self, database_id: str, token: str):
        if not token:
            raise ValueError("token do Notion não configurado")
        if not database_id:
            raise ValueError("database_id do Notion não configurado")

        self.client = Client(auth=token)
        self.database_id = database_id
        self._validate_database_properties()

    def insert_products(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Insere múltiplos produtos na base Notion

        Args:
            products: Lista de produtos validados

        Returns:
            Dicionário com resultado da operação:
            {
                "success": int,
                "failed": int,
                "errors": List[str]
            }
        """
        result = {
            "success": 0,
            "failed": 0,
            "errors": []
        }

        for idx, product in enumerate(products):
            try:
                self._insert_single_product(product)
                result["success"] += 1
                logger.info(f"Produto {idx + 1}/{len(products)} inserido: {product['Produto']}")
            except Exception as e:
                result["failed"] += 1
                error_msg = f"Erro ao inserir '{product.get('Produto', 'desconhecido')}': {str(e)}"
                result["errors"].append(error_msg)
                logger.error(error_msg)

        return result

    def _insert_single_product(self, product: Dict[str, Any]):
        """
        Insere um único produto na base Notion

        Args:
            product: Dicionário com dados validados do produto
        """
        product_emoji = self._resolve_product_emoji(product)

        properties = {
            "Produto": {
                "title": [
                    {
                        "text": {
                            "content": product["Produto"]
                        }
                    }
                ]
            },
            "Data": {
                "date": {
                    "start": product["Data"]
                }
            },
            "Categoria": {
                "select": {
                    "name": product["Categoria"]
                }
            },
            "Tipo": {
                "rich_text": [
                    {
                        "text": {
                            "content": product["Tipo"]
                        }
                    }
                ]
            },
            "Qnt.": {
                "number": product["Qnt"]
            },
            "Valor": {
                "number": product["Valor"]
            },
            "Desconto": {
                "number": product["Desconto"]
            },
            "Forma de Pagamento": {
                "select": {
                    "name": product["FormaDePagamento"]
                }
            }
        }

        self.client.pages.create(
            parent={"database_id": self.database_id},
            icon={"type": "emoji", "emoji": product_emoji},
            properties=properties
        )

    @staticmethod
    def _resolve_product_emoji(product: Dict[str, Any]) -> str:
        """Usa o emoji vindo do modelo quando válido; caso contrário usa ícone neutro."""
        emoji = str(product.get("Emoji", "")).strip()
        if ReceiptParser.is_valid_emoji(emoji):
            return emoji

        return DEFAULT_PRODUCT_EMOJI

    def _validate_database_properties(self) -> None:
        """
        Valida se a database possui exatamente as propriedades esperadas.
        """
        database = self.client.databases.retrieve(self.database_id)
        db_properties = database.get("properties", {})

        for property_name, expected_type in {
            "Produto": "title",
            "Data": "date",
            "Categoria": "select",
            "Tipo": "rich_text",
            "Qnt.": "number",
            "Valor": "number",
            "Desconto": "number",
            "Forma de Pagamento": "select",
        }.items():
            prop = db_properties.get(property_name)
            if not prop or prop.get("type") != expected_type:
                raise ValueError(
                    f"Propriedade obrigatória não encontrada para '{property_name}' "
                    f"(nome esperado: '{property_name}', tipo esperado: '{expected_type}')"
                )

        logger.info("Schema da database do Notion validado com sucesso")
