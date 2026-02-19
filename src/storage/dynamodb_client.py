"""
Cliente DynamoDB para rastreamento de update_ids processados
"""
import os
import logging
import time
from typing import Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class DynamoDBClient:
    """Cliente para armazenar update_ids processados"""

    def __init__(self):
        self.table_name = os.environ.get('DYNAMODB_TABLE_NAME')
        if not self.table_name:
            raise ValueError("DYNAMODB_TABLE_NAME não configurada")
        
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(self.table_name)
        
        # TTL: 7 dias (Telegram não reenvia updates muito antigos)
        self.ttl_seconds = 7 * 24 * 60 * 60

    def is_processed(self, update_id: int) -> bool:
        """
        Verifica se um update_id já foi processado
        
        Args:
            update_id: ID do update do Telegram
            
        Returns:
            True se já foi processado, False caso contrário
        """
        try:
            response = self.table.get_item(
                Key={'update_id': str(update_id)}
            )
            
            exists = 'Item' in response
            if exists:
                logger.info(f"Update {update_id} já foi processado anteriormente")
            
            return exists
            
        except ClientError as e:
            logger.error(f"Erro ao verificar update_id no DynamoDB: {e}")
            # Em caso de erro, deixa processar (fail open)
            return False

    def mark_as_processed(self, update_id: int) -> bool:
        """
        Marca um update_id como processado
        
        Args:
            update_id: ID do update do Telegram
            
        Returns:
            True se marcado com sucesso, False em caso de erro
        """
        try:
            ttl = int(time.time()) + self.ttl_seconds
            
            self.table.put_item(
                Item={
                    'update_id': str(update_id),
                    'processed_at': int(time.time()),
                    'ttl': ttl
                }
            )
            
            logger.info(f"Update {update_id} marcado como processado (TTL: {ttl})")
            return True
            
        except ClientError as e:
            logger.error(f"Erro ao marcar update_id no DynamoDB: {e}")
            return False
