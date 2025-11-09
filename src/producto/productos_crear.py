import os, json, boto3
from src.common.auth import get_token_from_headers, validate_token_and_get_claims

PRODUCTS_TABLE = os.environ["PRODUCTS_TABLE"]

def _resp(code, body): return {"statusCode": code, "body": json.dumps(body, ensure_ascii=False)}

def lambda_handler(event, context):
    token = get_token_from_headers(event)
    auth = validate_token_and_get_claims(token)
    if auth.get("statusCode") == 403:
        return _resp(403, {"error":"Acceso no autorizado"})
    tenant_id = auth.get("tenant_id")
    if not tenant_id:
        return _resp(400, {"error":"Token sin tenant_id"})

    body = json.loads(event.get("body") or "{}")
    body["tenant_id"] = tenant_id

    for req in ("product_id", "nombre"):
        if req not in body:
            return _resp(422, {"error": f"Falta {req}"})

    ddb = boto3.resource("dynamodb")
    table = ddb.Table(PRODUCTS_TABLE)
    try:
        table.put_item(
            Item=body,
            ConditionExpression="attribute_not_exists(tenant_id) AND attribute_not_exists(product_id)"
        )
    except ddb.meta.client.exceptions.ConditionalCheckFailedException:
        return _resp(409, {"error":"El producto ya existe"})
    return _resp(201, {"ok": True, "item": body})
