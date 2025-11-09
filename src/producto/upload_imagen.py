import os, json, base64, boto3
from botocore.exceptions import ClientError

PRODUCTS_BUCKET = os.environ.get("PRODUCTS_BUCKET")

def _resp(code, body):
    return {"statusCode": code, "body": json.dumps(body, ensure_ascii=False)}

def lambda_handler(event, context):
    try:

        body = json.loads(event.get("body") or "{}")
        bucket = PRODUCTS_BUCKET
        key = body.get("key")
        filename = body.get("filename")
        file_b64 = body.get("file_base64")
        content_type = body.get("content_type")

        if not bucket:
            return _resp(400, {"error":"Falta 'bucket'"})
        
        # Si no se proporciona el 'key', usa el 'filename' como el nombre del archivo
        if not key:
            if not filename:
                return _resp(400, {"error":"Falta 'filename'"})
            key = filename

        if not file_b64:
            return _resp(400, {"error":"'file_base64' es requerido"})

        try:
            file_bytes = base64.b64decode(file_b64)
        except Exception as e:
            return _resp(400, {"error": f"file_base64 inválido: {e}"})

        s3 = boto3.client("s3")
        put_kwargs = {"Bucket": bucket, "Key": key, "Body": file_bytes}
        if content_type:
            put_kwargs["ContentType"] = content_type

        resp = s3.put_object(**put_kwargs)
        etag = (resp.get("ETag") or "").strip('"')

        return _resp(200, {
            "bucket": bucket, "key": key,
            "size_bytes": len(file_bytes), "etag": etag,
            "message": "Archivo subido correctamente."
        })

    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if code == "AccessDenied":
            return _resp(403, {"error":"Acceso denegado al bucket"})
        if code == "NoSuchBucket":
            return _resp(400, {"error": f"El bucket {bucket} no existe"})
        return _resp(400, {"error": f"Error S3: {e}"})
    except Exception as e:
        return _resp(500, {"error": f"Error interno: {e}"})
