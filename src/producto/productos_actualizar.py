import os, json, boto3
from boto3.dynamodb.conditions import Key
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

    product_id = (event.get("pathParameters") or {}).get("product_id")
    if not product_id:
        return _resp(400, {"error":"Falta path param product_id"})

    body = json.loads(event.get("body") or "{}")
    # No permitir modificar llaves
    body.pop("tenant_id", None)
    body.pop("product_id", None)
    if not body:
        return _resp(400, {"error":"Body vacío; nada que actualizar"})

    # Build UpdateExpression
    expr_names, expr_values, sets = {}, {}, []
    for i, (k, v) in enumerate(body.items(), start=1):
        expr_names[f"#f{i}"] = k
        expr_values[f":v{i}"] = v
        sets.append(f"#f{i} = :v{i}")
    update_expr = "SET " + ", ".join(sets)

    ddb = boto3.resource("dynamodb")
    table = ddb.Table(PRODUCTS_TABLE)
    res = table.update_item(
        Key={"tenant_id": tenant_id, "product_id": product_id},
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
        ConditionExpression="attribute_exists(tenant_id) AND attribute_exists(product_id)",
        ReturnValues="ALL_NEW"
    )
    return _resp(200, {"ok": True, "item": res.get("Attributes")})
