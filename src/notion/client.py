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

PROPERTY_ALIASES = {
    "Produto": ["Produto"],
    "Data": ["Data"],
    "Categoria": ["Categoria"],
    "Tipo": ["Tipo"],
    "Qnt": ["Qnt.", "Qnt", "Quantidade"],
    "Valor": ["Valor", "Preço", "Preco", "Valor Total", "Preço Total", "Preco Total"],
    "Desconto": ["Desconto", "Desc.", "Descontos"],
    "FormaDePagamento": ["Forma de Pagamento", "FormaDePagamento", "Pagamento", "Forma Pagamento"],
}

EXPECTED_TYPES = {
    "Produto": "title",
    "Data": "date",
    "Categoria": "select",
    "Tipo": "rich_text",
    "Qnt": "number",
    "Valor": "number",
    "Desconto": "number",
    "FormaDePagamento": "select",
}

class NotionClient:
    """Cliente para inserir produtos na base Notion"""

    def __init__(self, database_id: str | None = None, token: str | None = None):
        resolved_token = token or os.environ.get('NOTION_TOKEN')
        resolved_database_id = database_id or os.environ.get('NOTION_DATABASE_ID')

        if not resolved_token:
            raise ValueError("NOTION_TOKEN não configurada")
        if not resolved_database_id:
            raise ValueError("NOTION_DATABASE_ID não configurada")

        self.client = Client(auth=resolved_token)
        self.database_id = resolved_database_id
        self.property_names = self._resolve_property_names()

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
            self.property_names["Produto"]: {
                "title": [
                    {
                        "text": {
                            "content": product_name
                        }
                    }
                ]
            },
            self.property_names["Data"]: {
                "date": {
                    "start": product["Data"]
                }
            },
            self.property_names["Categoria"]: {
                "select": {
                    "name": product["Categoria"]
                }
            },
            self.property_names["Tipo"]: {
                "rich_text": [
                    {
                        "text": {
                            "content": product["Tipo"]
                        }
                    }
                ]
            },
            self.property_names["Qnt"]: {
                "number": product["Qnt"]
            },
            self.property_names["Valor"]: {
                "number": product["Valor"]
            },
            self.property_names["Desconto"]: {
                "number": product["Desconto"]
            },
            self.property_names["FormaDePagamento"]: {
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

    def _resolve_property_names(self) -> Dict[str, str]:
        """
        Resolve os nomes reais das propriedades no database, aceitando aliases.
        Isso permite usar bases com variações de nomenclatura (ex.: Valor vs Preço).
        """
        database = self.client.databases.retrieve(self.database_id)
        db_properties = database.get("properties", {})

        resolved: Dict[str, str] = {}
        for logical_name, aliases in PROPERTY_ALIASES.items():
            expected_type = EXPECTED_TYPES[logical_name]
            selected_name = None

            # 1) Prioriza aliases com tipo correto
            for alias in aliases:
                prop = db_properties.get(alias)
                if prop and prop.get("type") == expected_type:
                    selected_name = alias
                    break

            # 2) Se não achou por alias, tenta case-insensitive
            if not selected_name:
                alias_map = {a.lower(): a for a in aliases}
                for actual_name, prop in db_properties.items():
                    if actual_name.lower() in alias_map and prop.get("type") == expected_type:
                        selected_name = actual_name
                        break

            # 3) Tenta comparação canônica (trim e espaços internos)
            if not selected_name:
                alias_canonical = {self._canonical_property_name(a) for a in aliases}
                for actual_name, prop in db_properties.items():
                    actual_canonical = self._canonical_property_name(actual_name)
                    if actual_canonical in alias_canonical and prop.get("type") == expected_type:
                        selected_name = actual_name
                        break

            if not selected_name:
                raise ValueError(
                    f"Propriedade obrigatória não encontrada para '{logical_name}' "
                    f"(esperado tipo '{expected_type}', aliases: {aliases})"
                )

            resolved[logical_name] = selected_name

        logger.info(f"Mapeamento de propriedades Notion: {resolved}")
        return resolved

    @staticmethod
    def _canonical_property_name(name: str) -> str:
        """Normaliza nome de propriedade para matching tolerante a espaços/case."""
        return re.sub(r"\s+", " ", str(name or "")).strip().lower()
