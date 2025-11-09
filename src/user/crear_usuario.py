import boto3
import hashlib

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def lambda_handler(event, context):
    try:
        tenant_id = event.get('tenant_id')
        user_id = event.get('user_id')
        password = event.get('password')
        
        if user_id and password:
            hashed_password = hash_password(password)
            dynamodb = boto3.resource('dynamodb')
            t_usuarios = dynamodb.Table('t_usuarios-dev')
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