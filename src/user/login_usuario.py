import boto3
import hashlib
import uuid
import json
import os
from datetime import datetime, timedelta


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def lambda_handler(event, context):
    # Parse body (HTTP API puts JSON string into event['body'])
    body = event.get('body', {}) or {}
    if isinstance(body, str):
        body = json.loads(body)

    tenant_id = body.get('tenant_id')
    user_id = body.get('user_id')
    password = body.get('password')

    if not (tenant_id and user_id and password):
        return {'statusCode': 400, 'body': 'Missing tenant_id, user_id or password'}

    hashed_password = hash_password(password)
    dynamodb = boto3.resource('dynamodb')
    users_table = os.environ.get('USERS_TABLE', 't_usuarios-dev')
    table = dynamodb.Table(users_table)
    response = table.get_item(
        Key={
            'tenant_id': tenant_id,
            'user_id': user_id
        }
    )
    if 'Item' not in response:
        return {
            'statusCode': 403,
            'body': 'Usuario no existe'
        }
    else:
        hashed_password_bd = response['Item']['password']
        if hashed_password == hashed_password_bd:
            token = str(uuid.uuid4())
            fecha_hora_exp = datetime.now() + timedelta(minutes=60)
            registro = {
                'token': token,
                'expires': fecha_hora_exp.strftime('%Y-%m-%d %H:%M:%S')
            }
            tokens_table = os.environ.get('TOKENS_TABLE', 't_tokens_acceso-dev')
            table = dynamodb.Table(tokens_table)
            dynamodbResponse = table.put_item(Item=registro)
        else:
            return {
                'statusCode': 403,
                'body': 'Password incorrecto'
            }

    # Salida (json)
    return {
        'statusCode': 200,
        'token': token
    }