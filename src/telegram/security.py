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
    authorized_single = os.environ.get('AUTHORIZED_USER_ID', '').strip()
    authorized_list_raw = os.environ.get('AUTHORIZED_USER_IDS', '').strip()

    authorized_ids = set()
    if authorized_single:
        authorized_ids.add(authorized_single)
    if authorized_list_raw:
        authorized_ids.update(uid.strip() for uid in authorized_list_raw.split(",") if uid.strip())

    if not authorized_ids:
        logger.error("AUTHORIZED_USER_ID/AUTHORIZED_USER_IDS não configurado")
        return False

    is_auth = user_id_str in authorized_ids
    if not is_auth:
        logger.warning(f"Acesso negado para usuário {user_id}")

    return is_auth


def get_user_notion_database_id(user_id: int) -> Optional[str]:
    """
    Resolve o database do Notion por usuário.

    Regras:
    1) Se existir em NOTION_DATABASE_BY_USER (JSON {"<telegram_user_id>": "<database_id>"}), usa esse valor.
    2) NOTION_DATABASE_ID só é aceito para AUTHORIZED_USER_ID (dono do bot).
    3) Outros usuários sem mapeamento explícito não têm base configurada.
    """
    mapping_raw = os.environ.get("NOTION_DATABASE_BY_USER", "").strip()
    fallback_database = os.environ.get("NOTION_DATABASE_ID", "").strip()
    owner_user_id = os.environ.get("AUTHORIZED_USER_ID", "").strip()
    user_id_str = str(user_id)

    if mapping_raw:
        try:
            mapping = json.loads(mapping_raw)
            if isinstance(mapping, dict):
                database_id = str(mapping.get(user_id_str, "")).strip()
                if database_id:
                    return database_id
        except json.JSONDecodeError:
            logger.error("NOTION_DATABASE_BY_USER inválido (JSON malformado)")

    if user_id_str == owner_user_id and fallback_database:
        return fallback_database

    return None
