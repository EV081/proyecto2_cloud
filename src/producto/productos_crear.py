import os, boto3, json

PRODUCTS_TABLE = os.environ["PRODUCTS_TABLE"]

def lambda_handler(event, context):
    print(event)

    # Body: string -> dict
    producto = json.loads(event.get('body') or "{}")

    # Headers seguros (evita KeyError) y soporta "Bearer ..."
    headers = event.get('headers') or {}
    token = headers.get('authorization') or headers.get('Authorization')
    if token and token.lower().startswith("bearer "):
        token = token[7:]

    if not token:
        return {
            'statusCode': 403,
            'status': 'Forbidden - Falta token'
        }

    # Validación de token
    lambda_client = boto3.client('lambda')
    payload_string = json.dumps({"token": token})
    invoke_response = lambda_client.invoke(
        FunctionName="ValidarTokenAcceso",
        InvocationType='RequestResponse',
        Payload=payload_string
    )
    validar = json.loads(invoke_response['Payload'].read() or "{}")
    print(validar)

    if validar.get('statusCode') == 403:
        return {
            'statusCode': 403,
            'status': 'Forbidden - Acceso No Autorizado'
        }

    # Proceso
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(PRODUCTS_TABLE)
    put_res = table.put_item(Item=producto)

    return {
        'statusCode': 200,
        'response': put_res
    }
