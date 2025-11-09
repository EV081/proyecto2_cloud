import os
import json
import uuid
import boto3
from botocore.exceptions import ClientError

VALIDAR_TOKEN_FN = os.getenv("VALIDAR_TOKEN_FN", "validar_token")
PRODUCTS_TABLE   = os.getenv("PRODUCTS_TABLE", "t_productos")

def _json_body(event):
    body = event.get('body', {}) or {}
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except Exception:
            body = {}
    return body

def _extraer_token(headers):
    if not headers:
        return None
    auth = headers.get('Authorization') or headers.get('authorization')
    if not auth:
        return None
    parts = auth.split()
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2 and parts[0].lower() == 'bearer':
        return parts[1]
    return None

def _validar_token(token):
    lambda_client = boto3.client('lambda')
    payload = json.dumps({"token": token})
    resp = lambda_client.invoke(
        FunctionName=VALIDAR_TOKEN_FN,
        InvocationType='RequestResponse',
        Payload=payload.encode('utf-8')
    )
    data = json.loads(resp['Payload'].read() or "{}")
    status = int(data.get("statusCode", 500))
    return (status == 200, data)

def lambda_handler(event, context):
    token = _extraer_token(event.get('headers', {}))
    if not token:
        return {"statusCode": 401, "error": "Falta header Authorization."}

    ok, _ = _validar_token(token)
    if not ok:
        return {"statusCode": 403, "status": "Forbidden - Acceso No Autorizado"}

    body = _json_body(event)
    producto = body.get("producto") or body
    image_key = body.get("image_key") or producto.get("image_key")
    imagen = producto.get("imagen") or {}
    bucket = body.get("bucket") or imagen.get("bucket")
    key = body.get("key") or imagen.get("key") or image_key

    if key:
        producto["imagen"] = {}
        if bucket:
            producto["imagen"]["bucket"] = bucket
        producto["imagen"]["key"] = key

        if bucket:
            s3 = boto3.client('s3')
            try:
                s3.head_object(Bucket=bucket, Key=key)
            except ClientError as e:
                return {
                    "statusCode": 400,
                    "error": f"La imagen no existe en S3: s3://{bucket}/{key}",
                    "detail": str(e)
                }

    if not producto:
        return {"statusCode": 400, "error": "Falta 'producto' en el body."}

    if "id" not in producto:
        producto["id"] = str(uuid.uuid4())
        
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(PRODUCTS_TABLE)
        result = table.put_item(Item=producto)
    except ClientError as e:
        return {"statusCode": 400, "error": str(e)}

    return {
        "statusCode": 200,
        "message": "Producto creado y asociado con imagen.",
        "producto": producto,
        "dynamodb_result": result
    }
