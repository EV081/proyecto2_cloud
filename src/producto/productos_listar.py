import os, json, boto3
from boto3.dynamodb.conditions import Key
from src.common.auth import get_token_from_headers, validate_token_and_get_claims

PRODUCTS_TABLE = os.environ["PRODUCTS_TABLE"]

def _resp(code, body):
    return {"statusCode": code, "body": json.dumps(body, ensure_ascii=False, default=str)}

def lambda_handler(event, context):
    token = get_token_from_headers(event)
    auth = validate_token_and_get_claims(token)
    if auth.get("statusCode") == 403:
        return _resp(403, {"error":"Acceso no autorizado"})

    body = json.loads(event.get("body") or "{}")
    tenant_id = body.get("tenant_id")
    if not tenant_id:
        return _resp(400, {"error":"Falta tenant_id en el body"})

    limit = body.get("limit", 10)
    try:
        limit = int(limit)
    except Exception:
        limit = 10
    if limit <= 0 or limit > 100:
        limit = 10

    last_key = body.get("next")  # dict o None

    ddb = boto3.resource("dynamodb")
    table = ddb.Table(PRODUCTS_TABLE)

    qargs = {"KeyConditionExpression": Key("tenant_id").eq(tenant_id), "Limit": limit}
    if last_key: qargs["ExclusiveStartKey"] = last_key

    r = table.query(**qargs)
    return _resp(200, {"items": r.get("Items", []), "next": r.get("LastEvaluatedKey")})
