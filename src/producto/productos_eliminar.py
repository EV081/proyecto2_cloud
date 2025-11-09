import os, json, boto3
from src.common.auth import get_token_from_headers, validate_token_and_get_claims

PRODUCTS_TABLE = os.environ["PRODUCTS_TABLE"]

def _resp(code, body): return {"statusCode": code, "body": json.dumps(body, ensure_ascii=False)}

def lambda_handler(event, context):
    token = get_token_from_headers(event)
    auth = validate_token_and_get_claims(token)
    if auth.get("statusCode") == 403:
        return _resp(403, {"error":"Acceso no autorizado"})

    product_id = (event.get("pathParameters") or {}).get("product_id")
    if not product_id:
        return _resp(400, {"error":"Falta path param product_id"})

    ddb = boto3.resource("dynamodb")
    table = ddb.Table(PRODUCTS_TABLE)
    try:
        res = table.delete_item(
            Key={"tenant_id": tenant_id, "product_id": product_id},
            ConditionExpression="attribute_exists(tenant_id) AND attribute_exists(product_id)",
            ReturnValues="ALL_OLD"
        )
    except ddb.meta.client.exceptions.ConditionalCheckFailedException:
        return _resp(404, {"error":"Producto no encontrado"})
    return _resp(200, {"ok": True, "deleted": res.get("Attributes")})
