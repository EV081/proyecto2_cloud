# src/producto/productos_obtener_post.py
import os, json, boto3
from common.auth import get_token_from_headers, validate_token_and_get_claims

PRODUCTS_TABLE = os.environ["PRODUCTS_TABLE"]

def _resp(code, body): 
    return {"statusCode": code, "body": json.dumps(body, ensure_ascii=False)}

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
    product_id = body.get("product_id")

    if not tenant_id:
        return _resp(400, {"error":"Falta tenant_id en el body"})
    if not product_id:
        return _resp(400, {"error":"Falta product_id en el body"})

    # opcional: exigir match con token
    if token_tenant and tenant_id != token_tenant:
        return _resp(403, {"error":"tenant_id del body no coincide con el token"})

    ddb = boto3.resource("dynamodb")
    table = ddb.Table(PRODUCTS_TABLE)
    r = table.get_item(Key={"tenant_id": tenant_id, "product_id": product_id})
    item = r.get("Item")
    if not item:
        return _resp(404, {"error":"Producto no encontrado"})
    return _resp(200, {"item": item})
