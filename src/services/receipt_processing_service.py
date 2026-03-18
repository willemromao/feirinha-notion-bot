"""Serviço de aplicação para processar uma nota fiscal enviada via Telegram."""
import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional

from notion.client import NotionClient
from processing.openai_client import OpenAIClient
from processing.receipt_parser import ReceiptParser

logger = logging.getLogger(__name__)


def looks_like_truncated_json(payload: str) -> bool:
    """Detecta respostas JSON provavelmente truncadas da OpenAI."""
    text = str(payload or "").strip()
    if not text:
        return False

    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    if not text.startswith("["):
        return False

    return text.count("[") > text.count("]") or text.count("{") > text.count("}")


@dataclass(frozen=True)
class ReceiptProcessingResult:
    """Resultado do processamento de uma nota."""

    ok: bool
    response_body: dict[str, Any]
    user_message: Optional[str] = None


class ReceiptProcessingService:
    """Orquestra o processamento completo da nota fiscal."""

    def __init__(
        self,
        telegram_handler: Any,
        notion_config_getter: Callable[[int], Optional[dict[str, str]]],
        openai_client_factory: Callable[[], OpenAIClient] = OpenAIClient,
        notion_client_factory: Callable[..., NotionClient] = NotionClient,
    ):
        self.telegram_handler = telegram_handler
        self.notion_config_getter = notion_config_getter
        self.openai_client_factory = openai_client_factory
        self.notion_client_factory = notion_client_factory

    def process_receipt(self, update_data: dict[str, Any]) -> ReceiptProcessingResult:
        """Executa o fluxo principal depois que o update já foi autenticado."""
        chat_id = update_data["chat_id"]
        message_id = update_data["message_id"]
        user_id = update_data["user_id"]
        payment_method = ReceiptParser.normalize_payment_method(update_data.get("caption", ""))

        logger.info(f"Processando foto do usuário {user_id}")

        if not payment_method:
            valid_options = ", ".join(ReceiptParser.list_payment_methods())
            return ReceiptProcessingResult(
                ok=False,
                user_message=(
                    "❌ Envie a foto com a forma de pagamento na legenda.\n\n"
                    f"Opções válidas: {valid_options}"
                ),
                response_body={"ok": False, "error": "Missing or invalid payment method"},
            )

        self.telegram_handler.send_message(
            chat_id,
            f"⏳ Processando sua nota fiscal com pagamento em *{payment_method}*... Isso pode levar alguns segundos.",
            message_id
        )

        image_bytes = self.telegram_handler.download_photo(update_data["photo"])
        if not image_bytes:
            return ReceiptProcessingResult(
                ok=False,
                user_message="❌ Falha ao baixar a imagem. Tente novamente.",
                response_body={"ok": False, "error": "Failed to download image"},
            )

        openai_client = self.openai_client_factory()
        extracted_data = openai_client.extract_receipt_data(image_bytes)
        if not extracted_data:
            return ReceiptProcessingResult(
                ok=False,
                user_message="❌ Falha ao processar a imagem com OpenAI. Tente novamente.",
                response_body={"ok": False, "error": "OpenAI processing failed"},
            )

        products = ReceiptParser.parse_openai_response(extracted_data, payment_method)
        if not products:
            if looks_like_truncated_json(extracted_data):
                return ReceiptProcessingResult(
                    ok=False,
                    user_message=(
                        "❌ A IA retornou uma resposta incompleta ao processar a nota. "
                        "Tente enviar a imagem novamente."
                    ),
                    response_body={"ok": False, "error": "Truncated OpenAI JSON response"},
                )

            return ReceiptProcessingResult(
                ok=False,
                user_message="❌ Não foi possível extrair produtos da nota fiscal. Verifique se a imagem está legível.",
                response_body={"ok": False, "error": "No products found"},
            )

        logger.info(f"Extraídos {len(products)} produtos")

        notion_config = self.notion_config_getter(user_id)
        if not notion_config:
            logger.error(f"Nenhuma configuração Notion válida para usuário {user_id}")
            return ReceiptProcessingResult(
                ok=False,
                user_message="❌ Configuração do Notion não encontrada para seu usuário.",
                response_body={"ok": False, "error": "Notion config not configured for user"},
            )

        notion_client = self.notion_client_factory(
            database_id=notion_config["database_id"],
            token=notion_config["token"],
        )
        insert_result = notion_client.insert_products(products)

        success_msg = f"✅ *{insert_result['success']} produtos cadastrados com sucesso!*"
        if insert_result["failed"] > 0:
            error_details = "\n".join(f"• {err}" for err in insert_result["errors"][:3])
            success_msg += f"\n\n⚠️ {insert_result['failed']} produtos falharam:\n{error_details}"
            if len(insert_result["errors"]) > 3:
                success_msg += f"\n\n_... e mais {len(insert_result['errors']) - 3} erro(s)_"

        return ReceiptProcessingResult(
            ok=True,
            user_message=success_msg,
            response_body={
                "ok": True,
                "products_inserted": insert_result["success"],
                "products_failed": insert_result["failed"],
            },
        )
