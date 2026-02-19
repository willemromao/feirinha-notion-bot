"""
Lambda handler principal para o bot Telegram
"""
import logging
import json
import threading
from telegram.security import validate_telegram_request, is_authorized_user
from telegram.handler import TelegramHandler
from processing.openai_client import OpenAIClient
from processing.receipt_parser import ReceiptParser
from notion.client import NotionClient

# Configuração de logging
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
        Resposta HTTP 200 imediatamente (processamento ocorre em background)
    """
    logger.info("Lambda invocada")

    try:
        # Valida request do Telegram (secret token)
        headers = event.get("headers", {})
        if not validate_telegram_request(headers):
            logger.warning("Request não autorizado (token inválido)")
            return create_response(200, {"ok": False, "error": "Unauthorized"})

        # Parse do body
        body = event.get("body", "{}")
        telegram = TelegramHandler()
        update_data = telegram.parse_update(body)

        if not update_data:
            logger.info("Update ignorado (não é foto ou inválido)")
            return create_response(200, {"ok": True, "message": "Update ignored"})

        chat_id = update_data["chat_id"]
        user_id = update_data["user_id"]
        message_id = update_data["message_id"]

        # Valida usuário autorizado
        if not is_authorized_user(user_id):
            telegram.send_message(
                chat_id,
                "❌ Você não está autorizado a usar este bot.",
                message_id
            )
            return create_response(200, {"ok": True, "message": "User not authorized"})

        logger.info(f"Processando foto do usuário {user_id}")

        # ⚡ RETORNA 200 IMEDIATAMENTE para o Telegram
        # Processamento pesado ocorre em background
        thread = threading.Thread(
            target=_process_receipt,
            args=(chat_id, user_id, message_id, update_data),
            daemon=True
        )
        thread.start()

        return create_response(200, {"ok": True, "message": "Processing started"})

    except Exception as e:
        logger.error(f"Erro crítico na validação: {e}", exc_info=True)
        return create_response(200, {"ok": False, "error": "Internal error"})


def _process_receipt(chat_id, user_id, message_id, update_data):
    """
    Processa a nota fiscal em background
    Não precisa retornar nada, apenas envia mensagens ao usuário
    """
    try:
        telegram = TelegramHandler()

        # Envia mensagem de aguarde
        telegram.send_message(
            chat_id,
            "⏳ Processando sua nota fiscal... Isso pode levar alguns segundos.",
            message_id
        )

        # Baixa a foto
        image_bytes = telegram.download_photo(update_data["photo"])
        if not image_bytes:
            telegram.send_message(
                chat_id,
                "❌ Falha ao baixar a imagem. Tente novamente.",
                message_id
            )
            return

        # Processa com OpenAI
        openai_client = OpenAIClient()
        extracted_data = openai_client.extract_receipt_data(image_bytes)

        if not extracted_data:
            telegram.send_message(
                chat_id,
                "❌ Falha ao processar a imagem com OpenAI. Tente novamente.",
                message_id
            )
            return

        # Parse e validação dos dados
        parser = ReceiptParser()
        products = parser.parse_openai_response(extracted_data)

        if not products:
            telegram.send_message(
                chat_id,
                "❌ Não foi possível extrair produtos da nota fiscal. Verifique se a imagem está legível.",
                message_id
            )
            return

        logger.info(f"Extraídos {len(products)} produtos")

        # Insere no Notion
        notion_client = NotionClient()
        result = notion_client.insert_products(products)

        # Monta mensagem de resultado
        success_msg = f"✅ *{result['success']} produtos cadastrados com sucesso!*"

        if result['failed'] > 0:
            error_details = "\n".join(f"• {err}" for err in result['errors'][:3])
            success_msg += f"\n\n⚠️ {result['failed']} produtos falharam:\n{error_details}"
            if len(result['errors']) > 3:
                success_msg += f"\n\n_... e mais {len(result['errors']) - 3} erro(s)_"

        telegram.send_message(chat_id, success_msg, message_id)

    except Exception as e:
        logger.error(f"Erro ao processar nota fiscal: {e}", exc_info=True)
        try:
            telegram.send_message(
                chat_id,
                "❌ Erro ao processar sua solicitação. Tente novamente mais tarde.",
                message_id
            )
        except:
            pass


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
