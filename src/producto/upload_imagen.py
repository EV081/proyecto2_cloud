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

    # Allow overriding the function name via env var; fallback strategies follow.
    func_name = os.environ.get('VALIDAR_TOKEN_FUNCTION')

    # Try invoking the remote Lambda if a function name is available.
    if func_name:
        try:
            resp = lambda_client.invoke(
                FunctionName=func_name,
                InvocationType='RequestResponse',
                Payload=payload.encode('utf-8')
            )
            data = json.loads(resp['Payload'].read() or "{}")
            status = int(data.get("statusCode", 500))
            return (status == 200, data)
        except Exception:
            # fall through to local-call fallback
            pass

    # Fallback: try to call the validator handler directly (same package).
    try:
        # local import to avoid circular imports at module load
        from src.seguridad.validar_token import lambda_handler as validar_handler
        # validator accepts either {"token": "..."} or event with body
        result = validar_handler({"token": token}, None)
        # result is expected to be a response dict with statusCode
        status = int(result.get("statusCode", 500))
        # normalise to match the previous return shape (body may be JSON string)
        body = result.get("body") or {}
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except Exception:
                body = {"message": body}
        data = {**body}
        data.setdefault("statusCode", status)
        return (status == 200, data)
    except Exception as e:
        # If everything fails, return a 500-like payload for the caller to handle.
        return (False, {"statusCode": 500, "error": str(e)})

def lambda_handler(event, context):
    token = _extraer_token(event.get('headers', {}))
    if not token:
        return {
            "statusCode": 401,
            "error": "Falta header Authorization."
        }

    ok, auth_payload = _validar_token(token)
    if not ok:
        return {
            "statusCode": 403,
            "status": "Forbidden - Acceso No Autorizado"
        }

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
