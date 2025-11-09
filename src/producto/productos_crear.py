import os, boto3, json

PRODUCTS_TABLE = os.environ["PRODUCTS_TABLE"]
VALIDAR_TOKEN_FN = os.environ.get("VALIDAR_TOKEN_FN", "millas-200-dev-ValidarTokenAcceso")

def lambda_handler(event, context):
    headers = event.get("headers") or {}
    token = headers.get("authorization") or headers.get("Authorization") or ""
    token = token.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    # LOG para depurar
    print({"token": token, "fn": VALIDAR_TOKEN_FN})

    lambda_client = boto3.client("lambda")
    payload_string = json.dumps({"token": token})
    resp = lambda_client.invoke(
        FunctionName=VALIDAR_TOKEN_FN,      # <- usa el nombre completo o ARN
        InvocationType="RequestResponse",
        Payload=payload_string
    )
    validar = json.loads(resp["Payload"].read() or "{}")
    print({"validar": validar})

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
