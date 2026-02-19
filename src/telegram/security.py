"""
Módulo de segurança para validação de requests do Telegram
"""
import os
import logging

logger = logging.getLogger(__name__)


def validate_telegram_request(headers: dict) -> bool:
    """
    Valida se o request vem do Telegram verificando o secret token

    Args:
        headers: Dicionário com os headers do request

    Returns:
        bool: True se válido, False caso contrário
    """
    expected_token = os.environ.get('TELEGRAM_SECRET_TOKEN', '')
    received_token = headers.get('x-telegram-bot-api-secret-token', '')

    if not expected_token:
        logger.error("TELEGRAM_SECRET_TOKEN não configurado")
        return False

    is_valid = received_token == expected_token
    if not is_valid:
        logger.warning("Token inválido recebido")

    return is_valid


def is_authorized_user(user_id: int) -> bool:
    """
    Verifica se o usuário está autorizado a usar o bot

    Args:
        user_id: ID do usuário no Telegram

    Returns:
        bool: True se autorizado, False caso contrário
    """
    authorized_id = os.environ.get('AUTHORIZED_USER_ID', '')

    if not authorized_id:
        logger.error("AUTHORIZED_USER_ID não configurado")
        return False

    is_auth = str(user_id) == authorized_id
    if not is_auth:
        logger.warning(f"Acesso negado para usuário {user_id}")

    return is_auth
