import os, json, math, boto3
from boto3.dynamodb.conditions import Key

PRODUCTS_TABLE = os.environ["PRODUCTS_TABLE"]

def _resp(code, body):
    return {"statusCode": code, "body": json.dumps(body, ensure_ascii=False, default=str)}

def _safe_int(v, default):
    try:
        return int(v)
    except Exception:
        return default

def lambda_handler(event, context):
    body = json.loads(event.get("body") or "{}")
    tenant_id = body.get("tenant_id")
    if not tenant_id:
        return _resp(400, {"error":"Falta tenant_id en el body"})

    # Parámetros de paginación estilo page/size
    page = _safe_int(body.get("page", 0), 0)
    size = _safe_int(body.get("size", body.get("limit", 10)), 10)  # aceptamos 'size' o 'limit'
    if size <= 0 or size > 100:
        size = 10
    if page < 0:
        page = 0

    ddb = boto3.resource("dynamodb")
    table = ddb.Table(PRODUCTS_TABLE)

    # 1) totalElements (Query con Select='COUNT' paginando por LastEvaluatedKey)
    total = 0
    count_args = {
        "KeyConditionExpression": Key("tenant_id").eq(tenant_id),
        "Select": "COUNT"
    }
    lek = None
    while True:
        if lek:
            count_args["ExclusiveStartKey"] = lek
        rcount = table.query(**count_args)
        total += rcount.get("Count", 0)
        lek = rcount.get("LastEvaluatedKey")
        if not lek:
            break

    total_pages = math.ceil(total / size) if size > 0 else 0

    # Si la página solicitada está fuera de rango, devolvemos vacío pero con totales correctos
    if total_pages and page >= total_pages:
        return _resp(200, {
            "contents": [],
            "page": page,
            "size": size,
            "totalElements": total,
            "totalPages": total_pages
        })

    # 2) Ir “saltando” hasta la página requerida usando ExclusiveStartKey
    qargs = {
        "KeyConditionExpression": Key("tenant_id").eq(tenant_id),
        "Limit": size
    }

    # Avanza page veces para posicionar el cursor
    lek = None
    for _ in range(page):
        if lek:
            qargs["ExclusiveStartKey"] = lek
        rskip = table.query(**qargs)
        lek = rskip.get("LastEvaluatedKey")
        if not lek:
            # Menos páginas de las que se pidieron: responder vacío coherente
            return _resp(200, {
                "contents": [],
                "page": page,
                "size": size,
                "totalElements": total,
                "totalPages": total_pages
            })

    # 3) Obtener contenidos de la página actual
    if lek:
        qargs["ExclusiveStartKey"] = lek
    rpage = table.query(**qargs)
    items = rpage.get("Items", [])

    # 4) Respuesta con shape de PaginatedResponse<T>
    return _resp(200, {
        "contents": items,
        "page": page,
        "size": size,
        "totalElements": total,
        "totalPages": total_pages
    })
