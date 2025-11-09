import json
import base64
import boto3
import os
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    """
    Espera en event['body']:
      {
        "bucket": "mi-bucket-123",
        "key": "carpeta/sub/archivo.pdf",
        "directory": "carpeta/sub/",
        "filename": "archivo.pdf",
        "file_base64": "<BASE64>",
        "content_type": "application/pdf"
      }
    """
    # Validar token de autorización
    token = event.get('headers', {}).get('Authorization')
    if not token:
        return {'statusCode': 401, 'error': 'Falta header Authorization.'}

    lambda_client = boto3.client('lambda')
    # Use configured function name if provided via env, otherwise fallback to literal
    validar_fn = os.environ.get('VALIDAR_TOKEN_FN', 'ValidarTokenAcceso')
    payload_string = json.dumps({"token": token})
    try:
        invoke_response = lambda_client.invoke(FunctionName=validar_fn, InvocationType='RequestResponse', Payload=payload_string)
        response = json.loads(invoke_response['Payload'].read())
        if response.get('statusCode') == 403:
            return {'statusCode': 403, 'status': 'Forbidden - Acceso No Autorizado'}
    except ClientError as e:
        return {'statusCode': 500, 'error': f'Error al invocar la función Lambda de validación: {str(e)}'}

    # Obtener parámetros del cuerpo
    body = event.get('body', {}) or {}
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except Exception:
            return {"statusCode": 400, "error": "El body no es JSON válido."}
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
        return {"statusCode": 400, "error": "'file_base64' es requerido y no puede estar vacío."}

    # Decodificar archivo base64
    try:
        file_bytes = base64.b64decode(file_b64)
    except Exception as e:
        return {"statusCode": 400, "error": f"El 'file_base64' no es válido: {str(e)}"}

    # Subir archivo a S3
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
        error_code = e.response['Error']['Code']
        if error_code == 'AccessDenied':
            return {"statusCode": 403, "error": "Acceso denegado al bucket de S3."}
        elif error_code == 'NoSuchBucket':
            return {"statusCode": 400, "error": f"El bucket {bucket} no existe."}
        return {"statusCode": 400, "error": f"Error al subir archivo a S3: {str(e)}"}
