"""
Parser para processar e validar dados extraídos de comprovantes
"""
import json
import logging
import re
from typing import List, Dict, Any, Optional, Tuple

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

        # Se vier apenas unidade (ex.: KG), converte para forma descritiva.
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
                # Fallback para Will
                forma_pagamento = "Will"

            # Valida tipos numéricos
            qnt = float(product["Qnt"])
            valor = float(product["Valor"])
            desconto = float(product.get("Desconto", 0))

            product_name = re.sub(r"\s+", " ", str(product["Produto"])).strip()
            product_name, extracted_measure = ReceiptParser._extract_measure_from_product(product_name)
            product_name = ReceiptParser._clean_product_name(product_name)
            normalized_type = ReceiptParser._normalize_type(product.get("Tipo", ""), qnt, extracted_measure)

            # Monta produto validado
            validated = {
                "Data": product["Data"],
                "Produto": product_name,
                "Tipo": normalized_type,
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
