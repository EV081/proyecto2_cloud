import boto3
import json

def lambda_handler(event, context):
    print(event)
    
    # Obtener el token desde los headers
    token = event['headers'].get('Authorization', '').strip()
    
    if not token:
        return {
            'statusCode': 400,
            'error': 'Falta el token en los headers (Authorization).'
        }

    # Validar token
    lambda_client = boto3.client('lambda')    
    payload_string = json.dumps({"token": token})
    
    try:
        invoke_response = lambda_client.invoke(
            FunctionName="ValidarTokenAcceso",
            InvocationType='RequestResponse',
            Payload=payload_string
        )
        response = json.loads(invoke_response['Payload'].read())
        print(response)
    except Exception as e:
        return {
            'statusCode': 500,
            'error': f'Error al invocar la función de validación: {str(e)}'
        }

    # Si la validación del token falla
    if response.get('statusCode') == 403:
        return {
            'statusCode': 403,
            'status': 'Forbidden - Acceso No Autorizado'
        }

    # Procesar el producto (suponiendo que el cuerpo tiene el formato adecuado)
    producto = event.get('body', {})

    if not producto:
        return {
            'statusCode': 400,
            'error': 'No se recibió el producto en el cuerpo de la solicitud.'
        }

    # Guardar el producto en DynamoDB
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('t_productos-dev')
    try:
        response = table.put_item(Item=producto)
    except Exception as e:
        return {
            'statusCode': 500,
            'error': f'Error al guardar el producto en DynamoDB: {str(e)}'
        }

    # Salida (json)
    return {
        'statusCode': 200,
        'message': 'Producto creado correctamente',
        'response': response
    }
