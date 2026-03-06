"""
Cliente para integração com Notion API
"""
import os
import logging
import re
from typing import List, Dict, Any
from notion_client import Client

logger = logging.getLogger(__name__)

EMOJI_BY_CATEGORY = {
    "Extra": "🧾",
    "Básico": "🥫",
    "Óleos/condimentos": "🧂",
    "Padaria": "🥖",
    "Bebidas": "🥤",
    "Carnes/ovos": "🥩",
    "Frios": "🧀",
    "Lanches/besteiras": "🍫",
    "Temperos": "🌿",
    "Grãos/mel": "🌾",
    "Frutas": "🍎",
    "Legumes/verduras": "🥕",
    "Limpeza": "🧴",
    "Higiene": "🧼",
}

EMOJI_BY_KEYWORD = [
    ("sardinha", "🐟"),
    ("atum", "🐟"),
    ("peixe", "🐟"),
    ("frango", "🍗"),
    ("carne", "🥩"),
    ("ovo", "🥚"),
    ("pão", "🥖"),
    ("queijo", "🧀"),
    ("presunto", "🥓"),
    ("iog", "🥛"),
    ("leite", "🥛"),
    ("café", "☕"),
    ("arroz", "🍚"),
    ("feijão", "🫘"),
    ("macarrão", "🍝"),
    ("molho", "🍅"),
    ("tomate", "🍅"),
    ("banana", "🍌"),
    ("maçã", "🍎"),
    ("batata", "🥔"),
    ("cebola", "🧅"),
    ("alho", "🧄"),
    ("chocolate", "🍫"),
    ("bisco", "🍪"),
    ("sorvete", "🍨"),
]

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
        product_name = self._normalize_product_name(product["Produto"])
        product_emoji = self._pick_product_emoji(
            product_name=product_name,
            category=product["Categoria"],
        )

        properties = {
            "Produto": {
                "title": [
                    {
                        "text": {
                            "content": product_name
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
    def _pick_product_emoji(product_name: str, category: str) -> str:
        """Seleciona emoji do item com base em palavra-chave e categoria."""
        normalized_name = product_name.lower()

        for keyword, emoji in EMOJI_BY_KEYWORD:
            if keyword in normalized_name:
                return emoji

        return EMOJI_BY_CATEGORY.get(category, "🛒")

    @staticmethod
    def _normalize_product_name(product_name: str) -> str:
        """
        Normaliza texto do produto:
        - remove espaços duplicados
        - se vier em caixa alta, converte para um title case legível
        """
        cleaned = re.sub(r"\s+", " ", str(product_name)).strip()
        if not cleaned:
            return cleaned

        # Heurística: OCR costuma enviar tudo em caixa alta.
        letters = [c for c in cleaned if c.isalpha()]
        if letters:
            upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
            if upper_ratio > 0.85:
                cleaned = cleaned.lower().title()

                # Ajustes simples para conectivos comuns em PT-BR.
                for word in [" De ", " Da ", " Do ", " Das ", " Dos ", " E "]:
                    cleaned = cleaned.replace(word, word.lower())

        return cleaned
