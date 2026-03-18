"""Schema e serialização da database do Notion."""
from typing import Any

from domain.product import ValidatedProduct

NOTION_DATABASE_SCHEMA = {
    "Produto": "title",
    "Data": "date",
    "Categoria": "select",
    "Tipo": "rich_text",
    "Qnt.": "number",
    "Valor": "number",
    "Desconto": "number",
    "Forma de Pagamento": "select",
}

DEFAULT_PRODUCT_EMOJI = "🛒"


def validate_database_schema(db_properties: dict[str, dict[str, Any]]) -> None:
    """Valida se a database possui exatamente as propriedades esperadas."""
    for property_name, expected_type in NOTION_DATABASE_SCHEMA.items():
        prop = db_properties.get(property_name)
        if not prop or prop.get("type") != expected_type:
            raise ValueError(
                f"Propriedade obrigatória não encontrada para '{property_name}' "
                f"(nome esperado: '{property_name}', tipo esperado: '{expected_type}')"
            )


def build_notion_properties(product: ValidatedProduct) -> dict[str, Any]:
    """Converte produto validado para o payload de propriedades do Notion."""
    return {
        "Produto": {
            "title": [
                {
                    "text": {
                        "content": product.produto
                    }
                }
            ]
        },
        "Data": {
            "date": {
                "start": product.data
            }
        },
        "Categoria": {
            "select": {
                "name": product.categoria
            }
        },
        "Tipo": {
            "rich_text": [
                {
                    "text": {
                        "content": product.tipo
                    }
                }
            ]
        },
        "Qnt.": {
            "number": product.qnt
        },
        "Valor": {
            "number": product.valor
        },
        "Desconto": {
            "number": product.desconto
        },
        "Forma de Pagamento": {
            "select": {
                "name": product.forma_de_pagamento
            }
        }
    }


def resolve_product_emoji(product: ValidatedProduct) -> str:
    """Usa o emoji validado pelo parser; caso contrário usa ícone neutro."""
    return product.emoji or DEFAULT_PRODUCT_EMOJI
