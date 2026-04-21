import importlib.util
import json
import os
import sys
import unittest


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))
MODULE_PATH = os.path.join(PROJECT_ROOT, "src", "processing", "receipt_parser.py")
SPEC = importlib.util.spec_from_file_location("receipt_parser_module", MODULE_PATH)
RECEIPT_PARSER_MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(RECEIPT_PARSER_MODULE)
ReceiptParser = RECEIPT_PARSER_MODULE.ReceiptParser


class ReceiptParserPaymentMethodTests(unittest.TestCase):
    def test_normalize_payment_method_accepts_common_variations(self):
        cases = {
            "Pix": "Pix",
            "pagamento: pix": "Pix",
            "especie": "Espécie",
            "Débito Inter": "Débito - Inter",
            "credito nubank": "Crédito - Nubank",
        }

        for raw_value, expected in cases.items():
            with self.subTest(raw_value=raw_value):
                self.assertEqual(ReceiptParser.normalize_payment_method(raw_value), expected)

    def test_normalize_payment_method_returns_none_for_invalid_input(self):
        self.assertIsNone(ReceiptParser.normalize_payment_method("cartao c6"))
        self.assertIsNone(ReceiptParser.normalize_payment_method(""))

    def test_parse_openai_response_injects_payment_method(self):
        response = json.dumps([
            {
                "Data": "2026-03-16",
                "Produto": "Leite Integral 1L",
                "Tipo": "UN",
                "Qnt": 1,
                "Valor": 8.99,
                "Desconto": 0,
                "Categoria": "Básico",
                "Emoji": "🥛",
            }
        ])

        products = ReceiptParser.parse_openai_response(response, "pagamento: pix")

        self.assertIsNotNone(products)
        self.assertEqual(products[0].forma_de_pagamento, "Pix")
        self.assertEqual(products[0].produto, "Leite Integral")
        self.assertEqual(products[0].emoji, "🥛")

    def test_parse_openai_response_ignores_invalid_emoji(self):
        response = json.dumps([
            {
                "Data": "2026-03-16",
                "Produto": "Tomate",
                "Tipo": "KG",
                "Qnt": 1,
                "Valor": 10.0,
                "Desconto": 0,
                "Categoria": "Frutas",
                "Emoji": "tomate",
            }
        ])

        products = ReceiptParser.parse_openai_response(response, "pix")

        self.assertIsNotNone(products)
        self.assertIsNone(products[0].emoji)

    def test_parse_openai_response_accepts_missing_tipo_and_desconto(self):
        response = json.dumps([
            {
                "Data": "2026-03-16",
                "Produto": "Arroz Branco 1KG",
                "Qnt": 1,
                "Valor": 7.5,
                "Categoria": "Básico",
            }
        ])

        products = ReceiptParser.parse_openai_response(response, "pix")

        self.assertIsNotNone(products)
        self.assertEqual(products[0].desconto, 0.0)
        self.assertEqual(products[0].tipo, "No peso - 1 kg")

    def test_parse_openai_response_rejects_invalid_payment_method(self):
        response = json.dumps([
            {
                "Data": "2026-03-16",
                "Produto": "Tomate",
                "Tipo": "KG",
                "Qnt": 1,
                "Valor": 10.0,
                "Desconto": 0,
                "Categoria": "Frutas",
            }
        ])

        self.assertIsNone(ReceiptParser.parse_openai_response(response, "cartao c6"))

    def test_parse_caption_extracts_payment_and_manual_date_ddmmaa(self):
        payment_method, manual_date = ReceiptParser.parse_caption("pix\n15/03/26")

        self.assertEqual(payment_method, "Pix")
        self.assertEqual(manual_date, "2026-03-15")

    def test_parse_caption_extracts_payment_and_manual_date_ddmmaaaa(self):
        payment_method, manual_date = ReceiptParser.parse_caption("Débito Inter\n05/01/2026")

        self.assertEqual(payment_method, "Débito - Inter")
        self.assertEqual(manual_date, "2026-01-05")

    def test_parse_caption_without_date_keeps_none(self):
        payment_method, manual_date = ReceiptParser.parse_caption("Crédito Nubank")

        self.assertEqual(payment_method, "Crédito - Nubank")
        self.assertIsNone(manual_date)

    def test_parse_caption_with_invalid_date_falls_back_to_none(self):
        payment_method, manual_date = ReceiptParser.parse_caption("pix\n00/00/00")

        self.assertEqual(payment_method, "Pix")
        self.assertIsNone(manual_date)

    def test_parse_openai_response_applies_override_date(self):
        response = json.dumps([
            {
                "Data": "2026-03-16",
                "Produto": "Leite Integral 1L",
                "Tipo": "UN",
                "Qnt": 1,
                "Valor": 8.99,
                "Desconto": 0,
                "Categoria": "Básico",
                "Emoji": "🥛",
            },
            {
                "Data": "2026-03-17",
                "Produto": "Tomate",
                "Tipo": "KG",
                "Qnt": 1,
                "Valor": 10.0,
                "Desconto": 0,
                "Categoria": "Frutas",
                "Emoji": "🍅",
            },
        ])

        products = ReceiptParser.parse_openai_response(
            response,
            "pix",
            override_date="2026-04-20",
        )

        self.assertIsNotNone(products)
        self.assertEqual(products[0].data, "2026-04-20")
        self.assertEqual(products[1].data, "2026-04-20")


if __name__ == "__main__":
    unittest.main()
