"""
Handler para processar mensagens do Telegram
"""
import os
import json
import logging
import httpx
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class TelegramHandler:
    """Handler para processar updates do Telegram"""

    def __init__(self):
        self.bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN não configurada")

        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    def parse_update(self, body: str) -> Optional[Dict[str, Any]]:
        """
        Faz parse do update recebido do Telegram

        Args:
            body: Corpo do request em JSON

        Returns:
            Dicionárgpt 3 tem quantas dimensoes?io com dados do update ou None se inválido
        """
        try:
            update = json.loads(body)

            if "message" not in update:
                logger.info("Update não contém mensagem")
                return None

            message = update["message"]

            if "photo" not in message:
                logger.info("Mensagem não contém foto")
                return None

            return {
                "update_id": update.get("update_id"),
                "chat_id": message["chat"]["id"],
                "user_id": message["from"]["id"],
                "message_id": message["message_id"],
                "photo": message["photo"],
                "caption": message.get("caption", ""),
            }

        except json.JSONDecodeError as e:
            logger.error(f"Erro ao fazer parse do update: {e}")
            return None
        except KeyError as e:
            logger.error(f"Estrutura do update inválida: {e}")
            return None

    def download_photo(self, photo_array: list) -> Optional[bytes]:
        """
        Baixa a foto de maior resolução dos servidores do Telegram

        Args:
            photo_array: Array de objetos PhotoSize do Telegram

        Returns:
            Bytes da imagem ou None em caso de erro
        """
        try:
            largest_photo = photo_array[-1]
            file_id = largest_photo["file_id"]

            logger.info(f"Baixando foto file_id={file_id}")

            with httpx.Client() as client:
                response = client.get(f"{self.base_url}/getFile?file_id={file_id}")
                response.raise_for_status()
                file_info = response.json()

            if not file_info.get("ok"):
                logger.error("Falha ao obter informações do arquivo")
                return None

            file_path = file_info["result"]["file_path"]
            file_url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"

            with httpx.Client() as client:
                response = client.get(file_url)
                response.raise_for_status()
                image_bytes = response.content

            logger.info(f"Foto baixada: {len(image_bytes)} bytes")
            return image_bytes

        except httpx.HTTPError as e:
            logger.error(f"Erro HTTP ao baixar foto: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao baixar foto: {e}")
            return None

    def send_message(self, chat_id: int, text: str, reply_to_message_id: Optional[int] = None):
        """
        Envia mensagem de texto para o usuário

        Args:
            chat_id: ID do chat
            text: Texto da mensagem
            reply_to_message_id: ID da mensagem a responder (opcional)
        """
        try:
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }

            if reply_to_message_id:
                payload["reply_to_message_id"] = reply_to_message_id

            with httpx.Client() as client:
                response = client.post(
                    f"{self.base_url}/sendMessage",
                    json=payload
                )
                response.raise_for_status()

            logger.info(f"Mensagem enviada para chat_id={chat_id}")

        except httpx.HTTPError as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado ao enviar mensagem: {e}")
