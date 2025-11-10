import os, json, boto3
from decimal import Decimal
from src.common.auth import get_token_from_headers, validate_token_and_get_claims

PRODUCTS_TABLE = os.environ["PRODUCTS_TABLE"]
UPLOAD_IMAGE_LAMBDA_NAME = os.environ["UPLOAD_IMAGE_LAMBDA_NAME"]

def _resp(code, body):
    return {"statusCode": code, "body": json.dumps(body, ensure_ascii=False, default=str)}

def lambda_handler(event, context):
    token = get_token_from_headers(event)
    auth = validate_token_and_get_claims(token)
    if auth.get("statusCode") == 403:
        return _resp(403, {"error": "Acceso no autorizado"})

    body = json.loads(event.get("body") or "{}", parse_float=Decimal)
    tenant_id = body.get("tenant_id")
    product_id = body.get("product_id")
    if not tenant_id:
        return _resp(400, {"error": "Falta tenant_id en el body"})
    if not product_id:
        return _resp(400, {"error": "Falta product_id en el body"})

    image_data = body.get("image")  # Obtener los datos de la imagen
    image_url_or_key = None  # Inicializar la variable

    if image_data:
        try:
            lambda_client = boto3.client("lambda")
            response = lambda_client.invoke(
                FunctionName=UPLOAD_IMAGE_LAMBDA_NAME,
                InvocationType='RequestResponse',
                Payload=json.dumps({
                    "key": body["image"]["key"],
                    "file_base64": body["image"]["file_base64"],
                    "content_type": body["image"]["content_type"]
                })
            )

            # Obtener la respuesta de upload_image
            image_response = json.loads(response['Payload'].read().decode())
            if response["StatusCode"] != 200:
                return _resp(400, {"error": "Error al subir la imagen", "details": image_response})

            # Verifica que la respuesta tenga la clave 'key' o 'url'
            image_url_or_key = image_response.get("key")  # Ahora obtenemos 'key' de la respuesta

        except Exception as e:
            return _resp(500, {"error": f"Error al invocar el Lambda de subida de imagen: {str(e)}"})

    # Guardar solo el 'key' en DynamoDB
    ddb = boto3.resource("dynamodb")
    table = ddb.Table(PRODUCTS_TABLE)
    try:
        body["image_url"] = image_url_or_key  # Guardamos solo el 'key' de la imagen
        table.put_item(
            Item=body,
            ConditionExpression="attribute_not_exists(tenant_id) AND attribute_not_exists(product_id)"
        )
    except ddb.meta.client.exceptions.ConditionalCheckFailedException:
        return _resp(409, {"error": "El producto ya existe"})

    return _resp(201, {"ok": True, "item": body})
