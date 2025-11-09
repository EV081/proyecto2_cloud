import os, boto3
import json

PRODUCTS_TABLE = os.environ["PRODUCTS_TABLE"]

def lambda_handler(event, context):
    print(event)
    # Entrada (json)
    producto = event['body']
    
    # Inicio - Proteger el Lambda
    token = headers.get('authorization') or headers.get('Authorization')
    lambda_client = boto3.client('lambda')    
    payload_string = '{ "token": "' + token +  '" }'
    invoke_response = lambda_client.invoke(FunctionName="ValidarTokenAcceso",
                                           InvocationType='RequestResponse',
                                           Payload = payload_string)
    response = json.loads(invoke_response['Payload'].read())
    print(response)
    if response['statusCode'] == 403:
        return {
            'statusCode' : 403,
            'status' : 'Forbidden - Acceso No Autorizado'
        }
    # Fin - Proteger el Lambda        

    # Proceso
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(PRODUCTS_TABLE)
    response = table.put_item(Item=producto)
    # Salida (json)
    return {
        'statusCode': 200,
        'response': response
    }