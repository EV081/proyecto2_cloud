import boto3
import hashlib
import json
import os


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def lambda_handler(event, context):
    try:
        # HTTP API events usually put the payload in event['body'] as a JSON string.
        body = event.get('body', {}) or {}
        if isinstance(body, str):
            body = json.loads(body)

        tenant_id = body.get('tenant_id')
        user_id = body.get('user_id')
        password = body.get('password')

        if user_id and password:
            hashed_password = hash_password(password)
            dynamodb = boto3.resource('dynamodb')
            users_table = os.environ.get('USERS_TABLE', 't_usuarios-dev')
            t_usuarios = dynamodb.Table(users_table)
            t_usuarios.put_item(
                Item={
                    'tenant_id': tenant_id,
                    'user_id': user_id,
                    'password': hashed_password,
                }
            )
            mensaje = {
                'message': 'User registered successfully',
                'user_id': user_id
            }
            return {
                'statusCode': 200,
                'body': mensaje
            }
        else:
            mensaje = {
                'error': 'Invalid request body: missing user_id or password'
            }
            return {
                'statusCode': 400,
                'body': mensaje
            }

    except Exception as e:
        print("Exception:", str(e))
        mensaje = {
            'error': str(e)
        }
        return {
            'statusCode': 500,
            'body': mensaje
        }