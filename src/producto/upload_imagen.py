import boto3
import os
import json
import base64
from botocore.exceptions import ClientError


def _json_body(event):
    body = event.get('body', {}) or {}
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except Exception:
            body = {}
    return body


def _extract_token_from_headers(headers):
    if not headers:
        return None
    auth = headers.get('Authorization') or headers.get('authorization')
    if not auth:
        return None
    parts = auth.split()
    if len(parts) == 0:
        return None
    if parts[0].lower() == 'bearer' and len(parts) >= 2:
        return parts[1]
    return parts[-1]


def _validar_token(token):
    try:
        from src.seguridad.validar_token import lambda_handler as validar_handler
        # validar_token accepts either an event with body or a direct {'token': token}
        result = validar_handler({"token": token}, None)
        status = int(result.get('statusCode', 500))
        body = result.get('body') or {}
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except Exception:
                body = {"message": body}
        data = {**body}
        data.setdefault('statusCode', status)
        return (status == 200, data)
    except Exception as e:
        return (False, {"statusCode": 500, "error": str(e)})


def lambda_handler(event, context):
    # Token validation from headers
    token = _extract_token_from_headers(event.get('headers', {}))
    if not token:
        return {"statusCode": 401, "error": "Falta header Authorization."}

    ok, _ = _validar_token(token)
    if not ok:
        return {"statusCode": 403, "status": "Forbidden - Acceso No Autorizado"}

    # Body and upload logic
    body = _json_body(event)
    bucket = body.get('bucket')
    key = body.get('key')
    directory = body.get('directory')
    filename = body.get('filename')
    file_b64 = body.get('file_base64')
    content_type = body.get('content_type')

    if not bucket:
        return {"statusCode": 400, "error": "Falta 'bucket'."}
    if not key:
        if not (directory and filename):
            return {"statusCode": 400, "error": "Proporciona 'key' o ('directory' y 'filename')."}
        if not directory.endswith('/'):
            directory = directory + '/'
        key = directory + filename
    if not file_b64:
        return {"statusCode": 400, "error": "Falta 'file_base64'."}

    try:
        file_bytes = base64.b64decode(file_b64)
    except Exception:
        return {"statusCode": 400, "error": "El 'file_base64' no es válido."}

    try:
        s3 = boto3.client('s3')
        put_kwargs = {"Bucket": bucket, "Key": key, "Body": file_bytes}
        if content_type:
            put_kwargs["ContentType"] = content_type

        resp = s3.put_object(**put_kwargs)
        etag = resp.get('ETag', '').strip('"')

        return {
            "statusCode": 200,
            "bucket": bucket,
            "key": key,
            "size_bytes": len(file_bytes),
            "etag": etag,
            "message": "Archivo subido."
        }
    except ClientError as e:
        return {"statusCode": 400, "error": str(e)}
