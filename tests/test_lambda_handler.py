import json
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

for module_name in list(sys.modules):
    if module_name == "processing" or module_name.startswith("processing."):
        sys.modules.pop(module_name)

if "notion_client" not in sys.modules:
    notion_client_module = types.ModuleType("notion_client")
    notion_client_module.Client = object
    sys.modules["notion_client"] = notion_client_module

if "httpx" not in sys.modules:
    httpx_module = types.ModuleType("httpx")

    class HTTPError(Exception):
        pass

    class HTTPStatusError(HTTPError):
        def __init__(self, *args, response=None, **kwargs):
            super().__init__(*args)
            self.response = response

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    httpx_module.HTTPError = HTTPError
    httpx_module.HTTPStatusError = HTTPStatusError
    httpx_module.Client = Client
    httpx_module.post = MagicMock()
    sys.modules["httpx"] = httpx_module

if "boto3" not in sys.modules:
    boto3_module = types.ModuleType("boto3")
    boto3_module.resource = MagicMock()
    sys.modules["boto3"] = boto3_module

if "botocore.exceptions" not in sys.modules:
    botocore_module = types.ModuleType("botocore")
    botocore_exceptions_module = types.ModuleType("botocore.exceptions")

    class ClientError(Exception):
        pass

    botocore_exceptions_module.ClientError = ClientError
    sys.modules["botocore"] = botocore_module
    sys.modules["botocore.exceptions"] = botocore_exceptions_module

from services.receipt_processing_service import ReceiptProcessingResult
import lambda_handler as lambda_handler_module


class LambdaHandlerTests(unittest.TestCase):
    def test_lambda_handler_returns_unauthorized_for_invalid_secret(self):
        event = {"headers": {}, "body": "{}"}

        with patch.object(lambda_handler_module, "validate_telegram_request", return_value=False):
            response = lambda_handler_module.lambda_handler(event, None)

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(json.loads(response["body"]), {"ok": False, "error": "Unauthorized"})

    def test_lambda_handler_processes_valid_update_with_service(self):
        event = {
            "headers": {"x-telegram-bot-api-secret-token": "token"},
            "body": json.dumps({"message": {"fake": "payload"}}),
        }
        update_data = {
            "update_id": 123,
            "chat_id": 456,
            "user_id": 789,
            "message_id": 321,
            "photo": [{"file_id": "file"}],
            "caption": "pix",
        }
        service_result = ReceiptProcessingResult(
            ok=True,
            user_message="✅ *2 produtos cadastrados com sucesso!*",
            response_body={"ok": True, "products_inserted": 2, "products_failed": 0},
        )

        telegram = MagicMock()
        telegram.parse_update.return_value = update_data
        service = MagicMock()
        service.process_receipt.return_value = service_result
        db_client = MagicMock()
        db_client.is_processed.return_value = False

        with patch.object(lambda_handler_module, "validate_telegram_request", return_value=True), \
             patch.object(lambda_handler_module, "TelegramHandler", return_value=telegram), \
             patch.object(lambda_handler_module, "ReceiptProcessingService", return_value=service), \
             patch.object(lambda_handler_module, "DynamoDBClient", return_value=db_client), \
             patch.object(lambda_handler_module, "is_authorized_user", return_value=True):
            response = lambda_handler_module.lambda_handler(event, None)

        service.process_receipt.assert_called_once_with(update_data)
        telegram.send_message.assert_called_once_with(456, "✅ *2 produtos cadastrados com sucesso!*", 321)
        db_client.mark_as_processed.assert_called_once_with(123)
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(
            json.loads(response["body"]),
            {"ok": True, "products_inserted": 2, "products_failed": 0},
        )


if __name__ == "__main__":
    unittest.main()
