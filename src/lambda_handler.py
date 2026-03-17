"""
Lambda handler principal para o bot Telegram
"""
import logging
import json
from telegram.security import (
    validate_telegram_request,
    is_authorized_user,
    get_user_notion_database_id,
    get_user_notion_token,
)
from telegram.handler import TelegramHandler
from processing.openai_client import OpenAIClient
from processing.receipt_parser import ReceiptParser
from notion.client import NotionClient
from storage.dynamodb_client import DynamoDBClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _looks_like_truncated_json(payload: str) -> bool:
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


def lambda_handler(event, context):
    """
    Handler principal da função Lambda

    Args:
        event: Evento do API Gateway
        context: Contexto da Lambda

    Returns:
        Resposta HTTP (sempre 200 para evitar retries do Telegram)
    """
    logger.info("Lambda invocada")

    try:
        headers = event.get("headers", {})
        if not validate_telegram_request(headers):
            logger.warning("Request não autorizado (token inválido)")
            return create_response(200, {"ok": False, "error": "Unauthorized"})

        body = event.get("body", "{}")
        telegram = TelegramHandler()
        update_data = telegram.parse_update(body)

        if not update_data:
            logger.info("Update ignorado (não é foto ou inválido)")
            return create_response(200, {"ok": True, "message": "Update ignored"})

        update_id = update_data.get("update_id")
        chat_id = update_data["chat_id"]
        user_id = update_data["user_id"]
        message_id = update_data["message_id"]
        payment_method = ReceiptParser.normalize_payment_method(update_data.get("caption", ""))

        if update_id:
            db_client = DynamoDBClient()
            if db_client.is_processed(update_id):
                logger.info(f"Update {update_id} já processado, ignorando")
                return create_response(200, {"ok": True, "message": "Already processed"})

            db_client.mark_as_processed(update_id)

        if not is_authorized_user(user_id):
            telegram.send_message(
                chat_id,
                "❌ Você não está autorizado a usar este bot.",
                message_id
            )
            return create_response(200, {"ok": True, "message": "User not authorized"})

        logger.info(f"Processando foto do usuário {user_id}")

        if not payment_method:
            valid_options = ", ".join(ReceiptParser.list_payment_methods())
            telegram.send_message(
                chat_id,
                "❌ Envie a foto com a forma de pagamento na legenda.\n\n"
                f"Opções válidas: {valid_options}",
                message_id
            )
            return create_response(200, {"ok": False, "error": "Missing or invalid payment method"})

        telegram.send_message(
            chat_id,
            f"⏳ Processando sua nota fiscal com pagamento em *{payment_method}*... Isso pode levar alguns segundos.",
            message_id
        )

        image_bytes = telegram.download_photo(update_data["photo"])
        if not image_bytes:
            telegram.send_message(
                chat_id,
                "❌ Falha ao baixar a imagem. Tente novamente.",
                message_id
            )
            return create_response(200, {"ok": False, "error": "Failed to download image"})

        openai_client = OpenAIClient()
        extracted_data = openai_client.extract_receipt_data(image_bytes)

        if not extracted_data:
            telegram.send_message(
                chat_id,
                "❌ Falha ao processar a imagem com OpenAI. Tente novamente.",
                message_id
            )
            return create_response(200, {"ok": False, "error": "OpenAI processing failed"})

        parser = ReceiptParser()
        products = parser.parse_openai_response(extracted_data, payment_method)

        if not products:
            if _looks_like_truncated_json(extracted_data):
                telegram.send_message(
                    chat_id,
                    "❌ A IA retornou uma resposta incompleta ao processar a nota. Tente enviar a imagem novamente.",
                    message_id
                )
                return create_response(200, {"ok": False, "error": "Truncated OpenAI JSON response"})

            telegram.send_message(
                chat_id,
                "❌ Não foi possível extrair produtos da nota fiscal. Verifique se a imagem está legível.",
                message_id
            )
            return create_response(200, {"ok": False, "error": "No products found"})

        logger.info(f"Extraídos {len(products)} produtos")

        notion_database_id = get_user_notion_database_id(user_id)
        if not notion_database_id:
            logger.error(f"Nenhuma base Notion configurada para usuário {user_id}")
            telegram.send_message(
                chat_id,
                "❌ Base do Notion não configurada para seu usuário.",
                message_id
            )
            return create_response(200, {"ok": False, "error": "Notion database not configured for user"})

        notion_token = get_user_notion_token(user_id)
        if not notion_token:
            logger.error(f"Nenhum token Notion configurado para usuário {user_id}")
            telegram.send_message(
                chat_id,
                "❌ Token do Notion não configurado para seu usuário.",
                message_id
            )
            return create_response(200, {"ok": False, "error": "Notion token not configured for user"})

        notion_client = NotionClient(database_id=notion_database_id, token=notion_token)
        result = notion_client.insert_products(products)

        success_msg = f"✅ *{result['success']} produtos cadastrados com sucesso!*"

        if result['failed'] > 0:
            error_details = "\n".join(f"• {err}" for err in result['errors'][:3])
            success_msg += f"\n\n⚠️ {result['failed']} produtos falharam:\n{error_details}"
            if len(result['errors']) > 3:
                success_msg += f"\n\n_... e mais {len(result['errors']) - 3} erro(s)_"

        telegram.send_message(chat_id, success_msg, message_id)

        return create_response(200, {
            "ok": True,
            "products_inserted": result['success'],
            "products_failed": result['failed']
        })

    except Exception as e:
        logger.error(f"Erro crítico: {e}", exc_info=True)

        try:
            if 'telegram' in locals() and 'chat_id' in locals():
                telegram.send_message(
                    chat_id,
                    "❌ Erro interno ao processar sua solicitação. Tente novamente mais tarde.",
                    message_id if 'message_id' in locals() else None
                )
        except:
            pass

        return create_response(200, {"ok": False, "error": "Internal error"})


def create_response(status_code: int, body: dict) -> dict:
    """
    Cria resposta HTTP padronizada

    Args:
        status_code: Código HTTP
        body: Corpo da resposta

    Returns:
        Dicionário de resposta para API Gateway
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(body)
    }
