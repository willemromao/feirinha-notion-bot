"""
Cliente para integração com Notion API
"""
import logging
from typing import Any

from notion_client import Client
from domain.product import ValidatedProduct
from notion.schema import build_notion_properties, resolve_product_emoji, validate_database_schema

logger = logging.getLogger(__name__)

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

    def insert_products(self, products: list[ValidatedProduct]) -> dict[str, Any]:
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
                logger.info(f"Produto {idx + 1}/{len(products)} inserido: {product.produto}")
            except Exception as e:
                result["failed"] += 1
                error_msg = f"Erro ao inserir '{product.produto}': {str(e)}"
                result["errors"].append(error_msg)
                logger.error(error_msg)

        return result

    def _insert_single_product(self, product: ValidatedProduct) -> None:
        """
        Insere um único produto na base Notion

        Args:
            product: Produto validado
        """
        self.client.pages.create(
            parent={"database_id": self.database_id},
            icon={"type": "emoji", "emoji": resolve_product_emoji(product)},
            properties=build_notion_properties(product)
        )

    def _validate_database_properties(self) -> None:
        """
        Valida se a database possui exatamente as propriedades esperadas.
        """
        database = self.client.databases.retrieve(self.database_id)
        db_properties = database.get("properties", {})
        validate_database_schema(db_properties)
        logger.info("Schema da database do Notion validado com sucesso")
