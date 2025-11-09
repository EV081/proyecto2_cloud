# src/producto/productos_listar_post.py (sin base64)
import os, json, boto3
from boto3.dynamodb.conditions import Key
from common.auth import get_token_from_headers, validate_token_and_get_claims

PRODUCTS_TABLE = os.environ["PRODUCTS_TABLE"]

def _resp(code, body):
    # default=str para serializar Decimal u otros tipos de Dynamo
    return {"statusCode": code, "body": json.dumps(body, ensure_ascii=False, default=str)}

def lambda_handler(event, context):
    # auth
    token = get_token_from_headers(event)
    auth = validate_token_and_get_claims(token)
    if auth.get("statusCode") == 403:
        return _resp(403, {"error":"Acceso no autorizado"})
    token_tenant = auth.get("tenant_id")

    # body
    body = json.loads(event.get("body") or "{}")
    tenant_id = body.get("tenant_id")
    if not tenant_id:
        return _resp(400, {"error":"Falta tenant_id en el body"})

    # opcional: exigir match con token
    if token_tenant and tenant_id != token_tenant:
        return _resp(403, {"error":"tenant_id del body no coincide con el token"})

    # paginación
    limit = body.get("limit", 10)
    try:
        limit = int(limit)
    except Exception:
        limit = 10
    if limit <= 0 or limit > 100:
        limit = 10

    # ahora esperamos el LastEvaluatedKey como objeto JSON directamente
    last_key = body.get("next")  # dict o None

    ddb = boto3.resource("dynamodb")
    table = ddb.Table(PRODUCTS_TABLE)

    query_args = {
        "KeyConditionExpression": Key("tenant_id").eq(tenant_id),
        "Limit": limit
    }
    if last_key:
        query_args["ExclusiveStartKey"] = last_key

    r = table.query(**query_args)
    items = r.get("Items", [])
    next_key = r.get("LastEvaluatedKey")  # dict o None

    # devolvemos el LEK tal cual para que el cliente lo reenvíe en el próximo POST
    return _resp(200, {"items": items, "next": next_key})
