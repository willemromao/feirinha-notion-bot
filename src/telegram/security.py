"""
Módulo de segurança para validação de requests do Telegram
"""
import os
import logging
import json
from typing import Optional

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
    user_id_str = str(user_id)
    authorized_list_raw = os.environ.get('AUTHORIZED_USER_IDS', '').strip()
    authorized_ids = {uid.strip() for uid in authorized_list_raw.split(",") if uid.strip()}

    if not authorized_ids:
        logger.error("AUTHORIZED_USER_IDS não configurado")
        return False

    is_auth = user_id_str in authorized_ids
    if not is_auth:
        logger.warning(f"Acesso negado para usuário {user_id}")

    return is_auth


def get_user_notion_config(user_id: int) -> Optional[dict[str, str]]:
    """
    Resolve a configuração Notion por usuário.

    Espera NOTION_CONFIG_BY_USER no formato:
    {
        "<telegram_user_id>": {
            "database_id": "<database_id>",
            "token": "<notion_token>"
        }
    }
    """
    config_raw = os.environ.get("NOTION_CONFIG_BY_USER", "").strip()
    user_id_str = str(user_id)

    if not config_raw:
        logger.error("NOTION_CONFIG_BY_USER não configurado")
        return None

    try:
        config_by_user = json.loads(config_raw)
    except json.JSONDecodeError:
        logger.error("NOTION_CONFIG_BY_USER inválido (JSON malformado)")
        return None

    if not isinstance(config_by_user, dict):
        logger.error("NOTION_CONFIG_BY_USER inválido (esperado objeto JSON)")
        return None

    user_config = config_by_user.get(user_id_str)
    if not isinstance(user_config, dict):
        return None

    database_id = str(user_config.get("database_id", "")).strip()
    token = str(user_config.get("token", "")).strip()

    if not database_id or not token:
        logger.error(f"Configuração Notion incompleta para usuário {user_id}")
        return None

    return {
        "database_id": database_id,
        "token": token,
    }
