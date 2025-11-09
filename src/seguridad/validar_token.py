import boto3
import os
import json
from datetime import datetime


def lambda_handler(event, context):
    # Accept either direct {"token": "..."} or HTTP-style event with body string
    token = None
    if isinstance(event, dict):
        token = event.get('token')
        if not token and event.get('body'):
            try:
                body = event.get('body')
                if isinstance(body, str):
                    body = json.loads(body)
                token = body.get('token') if isinstance(body, dict) else None
            except Exception:
                pass

    if not token:
        return {'statusCode': 400, 'body': 'Token no provisto'}

    dynamodb = boto3.resource('dynamodb')
    tokens_table = os.environ.get('TOKENS_TABLE', 't_tokens_acceso-dev')
    table = dynamodb.Table(tokens_table)
    response = table.get_item(Key={'token': token})

    if 'Item' not in response:
        return {'statusCode': 403, 'body': 'Token no existe'}

    expires = response['Item'].get('expires')
    if expires:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if now > expires:
            return {'statusCode': 403, 'body': 'Token expirado'}

    # Salida (json)
    return {'statusCode': 200, 'body': 'Token válido'}