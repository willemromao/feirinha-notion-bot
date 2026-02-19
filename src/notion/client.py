"""
Cliente para integração com Notion API
"""
import os
import logging
from typing import List, Dict, Any
from notion_client import Client

logger = logging.getLogger(__name__)


class NotionClient:
    """Cliente para inserir produtos na base Notion"""

    def __init__(self):
        token = os.environ.get('NOTION_TOKEN')
        database_id = os.environ.get('NOTION_DATABASE_ID')

        if not token:
            raise ValueError("NOTION_TOKEN não configurada")
        if not database_id:
            raise ValueError("NOTION_DATABASE_ID não configurada")

        self.client = Client(auth=token)
        self.database_id = database_id

    def insert_products(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Insere múltiplos produtos na base Notion

        Args:
            products: Lista de produtos validados

        Returns:
            Dicionário com resultado da operação:
            {
                "success": int,  # Quantidade de produtos inseridos com sucesso
                "failed": int,   # Quantidade de falhas
                "errors": List[str]  # Lista de mensagens de erro
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
            properties=properties
        )
