"""
Lambda handler principal para o bot Telegram
"""
import logging
import json
from telegram.security import (
    validate_telegram_request,
    is_authorized_user,
    get_user_notion_config,
)
from telegram.handler import TelegramHandler
from services.receipt_processing_service import ReceiptProcessingService
from storage.dynamodb_client import DynamoDBClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
        processing_service = ReceiptProcessingService(
            telegram_handler=telegram,
            notion_config_getter=get_user_notion_config,
        )
        update_data = telegram.parse_update(body)

        if not update_data:
            logger.info("Update ignorado (não é foto ou inválido)")
            return create_response(200, {"ok": True, "message": "Update ignored"})

        update_id = update_data.get("update_id")
        chat_id = update_data["chat_id"]
        user_id = update_data["user_id"]
        message_id = update_data["message_id"]
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
        result = processing_service.process_receipt(update_data)
        if result.user_message:
            telegram.send_message(chat_id, result.user_message, message_id)
        return create_response(200, result.response_body)

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
