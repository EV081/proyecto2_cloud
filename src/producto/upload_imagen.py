import json
import base64
import boto3
import os
from botocore.exceptions import ClientError

def validate_token(token):
    lambda_client = boto3.client('lambda')
    validar_fn = os.environ.get('VALIDAR_TOKEN_FN', 'ValidarTokenAcceso')
    payload_string = json.dumps({"token": token})
    try:
        invoke_response = lambda_client.invoke(
            FunctionName=validar_fn,
            InvocationType='RequestResponse',
            Payload=payload_string
        )
        response = json.loads(invoke_response['Payload'].read())
        if response.get('statusCode') == 403:
            return False
        return response
    except ClientError as e:
        return False  # Si ocurre un error al invocar la Lambda de validación, retornamos falso.


def lambda_handler(event, context):
    try:
        # Obtener el token desde los headers
        token = (event['headers'].get('Authorization') or "").strip()
        if not token:
            return {"statusCode": 400, "error": "Falta el token en los headers (Authorization)."}

        # Validar token
        auth = validate_token(token)
        if not auth:
            return {"statusCode": 403, "error": "Token inválido."}
        
        tenant_id = auth.get("tenant_id")
        if not tenant_id:
            return {"statusCode": 400, "error": "Token no contiene tenant_id."}

        # Obtener parámetros del cuerpo de la solicitud
        body = json.loads(event.get('body', '{}'))
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
        s3 = boto3.client('s3')
        put_kwargs = {"Bucket": bucket, "Key": key, "Body": file_bytes}
        if content_type:
            put_kwargs["ContentType"] = content_type
        
        try:
            resp = s3.put_object(**put_kwargs)
            etag = resp.get('ETag', '').strip('"')

            return {
                "statusCode": 200,
                "bucket": bucket,
                "key": key,
                "size_bytes": len(file_bytes),
                "etag": etag,
                "message": "Archivo subido correctamente."
            }
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDenied':
                return {"statusCode": 403, "error": "Acceso denegado al bucket de S3."}
            elif error_code == 'NoSuchBucket':
                return {"statusCode": 400, "error": f"El bucket {bucket} no existe."}
            return {"statusCode": 400, "error": f"Error al subir archivo a S3: {str(e)}"}

    except Exception as e:
        return {"statusCode": 500, "error": f"Error interno: {str(e)}"}
