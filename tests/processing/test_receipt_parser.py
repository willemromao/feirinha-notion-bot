import importlib.util
import json
import os
import unittest


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
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
        self.assertEqual(products[0]["FormaDePagamento"], "Pix")
        self.assertEqual(products[0]["Produto"], "Leite Integral")
        self.assertEqual(products[0]["Emoji"], "🥛")

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
        self.assertNotIn("Emoji", products[0])

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


if __name__ == "__main__":
    unittest.main()
