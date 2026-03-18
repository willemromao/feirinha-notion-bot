import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

if "notion_client" not in sys.modules:
    notion_client_module = types.ModuleType("notion_client")
    notion_client_module.Client = object
    sys.modules["notion_client"] = notion_client_module

from notion.client import NotionClient


class NotionClientSchemaTests(unittest.TestCase):
    def test_validate_database_properties_accepts_expected_schema(self):
        database_properties = {
            "Produto": {"type": "title"},
            "Data": {"type": "date"},
            "Categoria": {"type": "select"},
            "Tipo": {"type": "rich_text"},
            "Qnt.": {"type": "number"},
            "Valor": {"type": "number"},
            "Desconto": {"type": "number"},
            "Forma de Pagamento": {"type": "select"},
        }

        mocked_sdk_client = MagicMock()
        mocked_sdk_client.databases.retrieve.return_value = {"properties": database_properties}

        with patch("notion.client.Client", return_value=mocked_sdk_client):
            NotionClient(database_id="db123", token="secret")

        mocked_sdk_client.databases.retrieve.assert_called_once_with("db123")

    def test_validate_database_properties_rejects_wrong_type(self):
        database_properties = {
            "Produto": {"type": "title"},
            "Data": {"type": "date"},
            "Categoria": {"type": "select"},
            "Tipo": {"type": "rich_text"},
            "Qnt.": {"type": "number"},
            "Valor": {"type": "rich_text"},
            "Desconto": {"type": "number"},
            "Forma de Pagamento": {"type": "select"},
        }

        mocked_sdk_client = MagicMock()
        mocked_sdk_client.databases.retrieve.return_value = {"properties": database_properties}

        with patch("notion.client.Client", return_value=mocked_sdk_client):
            with self.assertRaises(ValueError) as exc:
                NotionClient(database_id="db123", token="secret")

        self.assertIn("Valor", str(exc.exception))


if __name__ == "__main__":
    unittest.main()
