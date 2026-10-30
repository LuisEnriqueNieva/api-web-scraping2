import requests
import boto3
import uuid
from datetime import datetime

def lambda_handler(event, context):
    # URL de la API que usa la página de sismos del IGP (sismos del año actual)
    anio = datetime.now().year
    url = f"https://ultimosismo.igp.gob.pe/api/ultimo-sismo/ajaxb/{anio}"

    # Realizar la solicitud HTTP a la API
    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        return {
            'statusCode': response.status_code,
            'body': 'Error al acceder a la API del IGP'
        }

    # Leer el JSON con la lista de sismos
    sismos = response.json()
    if not sismos:
        return {
            'statusCode': 404,
            'body': 'No se encontraron sismos en la API del IGP'
        }

    # Quedarnos con los 10 sismos más recientes
    sismos = sorted(sismos, key=lambda s: s['idlistasismos'], reverse=True)[:10]

    # Armar las filas con los datos que nos interesan
    rows = []
    for s in sismos:
        rows.append({
            'codigo': s['codigo'],
            'referencia': s['referencia'],
            'fecha_local': s['fecha_local'][:10],
            'hora_local': s['hora_local'][11:19],
            'magnitud': s['magnitud'],
            'profundidad': s['profundidad'],
            'latitud': s['latitud'],
            'longitud': s['longitud'],
            'intensidad': s['intensidad']
        })

    # Guardar los datos en DynamoDB
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('TablaSismos')

    # Eliminar todos los elementos de la tabla antes de agregar los nuevos
    scan = table.scan()
    with table.batch_writer() as batch:
        for each in scan['Items']:
            batch.delete_item(
                Key={
                    'id': each['id']
                }
            )

    # Insertar los nuevos datos
    i = 1
    for row in rows:
        row['#'] = i
        row['id'] = str(uuid.uuid4())  # Generar un ID único para cada entrada
        table.put_item(Item=row)
        i = i + 1

    # Retornar el resultado como JSON
    return {
        'statusCode': 200,
        'body': rows
    }
