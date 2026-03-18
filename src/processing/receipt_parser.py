"""
Parser para processar e validar dados extraídos de comprovantes
"""
import json
import logging
import re
import unicodedata
from typing import List, Dict, Any, Optional, Tuple

from domain.product import ValidatedProduct

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

PAYMENT_METHOD_ALIASES = {
    "will": "Will",
    "especie": "Espécie",
    "dinheiro": "Espécie",
    "pix": "Pix",
    "debito inter": "Débito - Inter",
    "inter debito": "Débito - Inter",
    "credito inter": "Crédito - Inter",
    "inter credito": "Crédito - Inter",
    "debito nubank": "Débito - Nubank",
    "nubank debito": "Débito - Nubank",
    "credito nubank": "Crédito - Nubank",
    "nubank credito": "Crédito - Nubank",
}

UNIT_ALIASES = {
    "kg": "kg",
    "quilo": "kg",
    "quilograma": "kg",
    "g": "g",
    "gr": "g",
    "grama": "g",
    "gramas": "g",
    "ml": "ml",
    "l": "l",
    "lt": "l",
    "lts": "l",
    "un": "un",
    "und": "un",
    "unid": "un",
    "unidade": "un",
}

PACKAGE_ALIASES = {
    "pc": "Pacote",
    "pct": "Pacote",
    "pcte": "Pacote",
    "pacote": "Pacote",
    "cx": "Caixa",
    "caixa": "Caixa",
    "fr": "Frasco",
    "frasco": "Frasco",
    "gar": "Garrafa",
    "garrafa": "Garrafa",
    "lt": "Lata",
    "lata": "Lata",
    "pote": "Pote",
    "sache": "Sachê",
    "sachê": "Sachê",
}


def _format_decimal(value: float) -> str:
    """Formata número de forma legível para textos (ex.: 1,5)."""
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")


class ReceiptParser:
    """Parser para validar e estruturar dados de comprovantes"""

    @staticmethod
    def parse_openai_response(response: str, payment_method: str) -> Optional[List[ValidatedProduct]]:
        """
        Faz parse da resposta JSON da OpenAI e valida os dados

        Args:
            response: String JSON retornada pela OpenAI
            payment_method: Forma de pagamento já validada externamente

        Returns:
            Lista de produtos validados ou None em caso de erro
        """
        try:
            normalized_payment_method = ReceiptParser.normalize_payment_method(payment_method)
            if not normalized_payment_method:
                logger.error("Forma de pagamento inválida para o parse")
                return None

            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()

            products = json.loads(cleaned_response)

            if not isinstance(products, list):
                logger.error("Resposta da OpenAI não é um array")
                return None

            logger.info(f"OpenAI retornou {len(products)} item(ns) brutos")

            validated_products: List[ValidatedProduct] = []
            for idx, product in enumerate(products):
                validated = ReceiptParser._validate_product(product, idx, normalized_payment_method)
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
    def normalize_payment_method(raw_payment_method: str) -> Optional[str]:
        """Normaliza texto livre para uma forma de pagamento válida."""
        normalized = ReceiptParser._normalize_free_text(raw_payment_method)
        if not normalized:
            return None

        if normalized in PAYMENT_METHOD_ALIASES:
            return PAYMENT_METHOD_ALIASES[normalized]

        for alias, payment_method in PAYMENT_METHOD_ALIASES.items():
            if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", normalized):
                return payment_method

        return None

    @staticmethod
    def list_payment_methods() -> List[str]:
        """Retorna os valores oficiais aceitos pelo Notion."""
        return VALID_PAYMENT_METHODS.copy()

    @staticmethod
    def _normalize_free_text(value: str) -> str:
        """Remove acentos e pontuação para matching tolerante."""
        text = unicodedata.normalize("NFKD", str(value or ""))
        text = "".join(char for char in text if not unicodedata.combining(char))
        text = re.sub(r"[^a-zA-Z0-9]+", " ", text).strip().lower()
        return re.sub(r"\s+", " ", text)

    @staticmethod
    def is_valid_emoji(value: str) -> bool:
        """Aceita um único emoji simples para usar como ícone no Notion."""
        if not isinstance(value, str):
            return False

        cleaned = value.strip()
        if not cleaned:
            return False

        if len(cleaned) > 4:
            return False

        return any(
            ord(char) >= 0x2600 or unicodedata.category(char) == "So"
            for char in cleaned
        )

    @staticmethod
    def _extract_measure_from_product(product_name: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Extrai indicador de embalagem/medida no final do nome do produto.

        Exemplos reconhecidos:
        - "... Pc 480G"
        - "... 125 ml"
        - "... 2L"
        """
        if not product_name:
            return product_name, None

        pattern = re.compile(
            r"^(?P<name>.+?)\s+(?:(?P<pkg>pc|pct|pcte|pacote|cx|caixa|fr|frasco|gar|garrafa|lt|lata|pote|sache|sachê)\s+)?(?P<amount>\d+(?:[\.,]\d+)?)\s*(?P<unit>kg|g|gr|grama|gramas|ml|l|lt|lts|un|und|unid|unidade)$",
            re.IGNORECASE,
        )
        match = pattern.match(product_name.strip().rstrip("."))
        if not match:
            return product_name, None

        name = match.group("name").strip()
        pkg_raw = (match.group("pkg") or "").lower()
        amount_raw = match.group("amount").replace(",", ".")
        unit_raw = match.group("unit").lower()

        try:
            amount = float(amount_raw)
        except ValueError:
            return product_name, None

        unit = UNIT_ALIASES.get(unit_raw, unit_raw)
        package = PACKAGE_ALIASES.get(pkg_raw) if pkg_raw else None

        return name, {
            "package": package,
            "amount": amount,
            "unit": unit,
        }

    @staticmethod
    def _normalize_type(tipo: str, qnt: float, extracted_measure: Optional[Dict[str, Any]]) -> str:
        """Padroniza campo Tipo para manter consistência no Notion."""
        cleaned_tipo = re.sub(r"\s+", " ", str(tipo or "")).strip()

        if extracted_measure:
            package = extracted_measure["package"]
            amount = _format_decimal(extracted_measure["amount"])
            unit = extracted_measure["unit"]
            if package:
                return f"{package} de {amount} {unit}"
            return f"No peso - {amount} {unit}"

        unit_only = UNIT_ALIASES.get(cleaned_tipo.lower()) if cleaned_tipo else None
        if unit_only:
            if unit_only in {"kg", "g"}:
                if unit_only == "kg" and qnt > 0:
                    amount_in_g = qnt * 1000
                    return f"No peso - {_format_decimal(amount_in_g)} g"
                if unit_only == "g" and qnt > 0:
                    return f"No peso - {_format_decimal(qnt)} g"
                return f"No peso - 1 {unit_only}"
            if qnt > 0:
                return f"{_format_decimal(qnt)} {unit_only}"
            return f"1 {unit_only}"

        return cleaned_tipo

    @staticmethod
    def _clean_product_name(product_name: str) -> str:
        """Remove resíduos de unidade/embalagem ao final do nome do produto."""
        cleaned_name = re.sub(r"\s+", " ", str(product_name or "")).strip().strip(".")
        if not cleaned_name:
            return cleaned_name

        suffix_pattern = re.compile(
            r"\s+(kg|g|gr|ml|l|lt|un|und|unid|unidade|pc|pct|pcte)$",
            re.IGNORECASE,
        )
        while True:
            updated = suffix_pattern.sub("", cleaned_name).strip().strip(".")
            if updated == cleaned_name:
                break
            cleaned_name = updated

        return cleaned_name

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

        letters = [c for c in cleaned if c.isalpha()]
        if letters:
            upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
            if upper_ratio > 0.85:
                cleaned = cleaned.lower().title()

                for word in [" De ", " Da ", " Do ", " Das ", " Dos ", " E "]:
                    cleaned = cleaned.replace(word, word.lower())

        return cleaned

    @staticmethod
    def _validate_product(
        product: Dict[str, Any],
        index: int,
        payment_method: str,
    ) -> Optional[ValidatedProduct]:
        """
        Valida campos individuais de um produto

        Args:
            product: Dicionário com dados do produto
            index: Índice do produto na lista

        Returns:
            Produto validado ou None se inválido
        """
        try:
            required_fields = ["Data", "Produto", "Qnt", "Valor", "Categoria"]
            for field in required_fields:
                if field not in product:
                    logger.warning(f"Produto {index}: campo '{field}' ausente")
                    return None

            categoria = product["Categoria"]
            if categoria not in VALID_CATEGORIES:
                logger.warning(f"Produto {index}: categoria inválida '{categoria}'")
                categoria = "Extra"

            qnt = float(product["Qnt"])
            valor = float(product["Valor"])
            desconto = float(product.get("Desconto", 0))

            product_name = re.sub(r"\s+", " ", str(product["Produto"])).strip()
            product_name, extracted_measure = ReceiptParser._extract_measure_from_product(product_name)
            product_name = ReceiptParser._clean_product_name(product_name)
            product_name = ReceiptParser._normalize_product_name(product_name)
            normalized_type = ReceiptParser._normalize_type(product.get("Tipo", ""), qnt, extracted_measure)

            emoji = str(product.get("Emoji", "")).strip()
            validated_emoji = emoji if ReceiptParser.is_valid_emoji(emoji) else None

            return ValidatedProduct(
                data=product["Data"],
                produto=product_name,
                tipo=normalized_type,
                qnt=qnt,
                valor=valor,
                desconto=desconto,
                categoria=categoria,
                forma_de_pagamento=payment_method,
                emoji=validated_emoji,
            )

        except (ValueError, TypeError) as e:
            logger.warning(f"Produto {index}: erro de validação - {e}")
            return None
