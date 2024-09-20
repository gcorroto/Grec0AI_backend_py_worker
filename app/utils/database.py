import mysql.connector
import os
from dotenv import load_dotenv

# Cargar las variables desde el archivo .env
load_dotenv()

def get_db_connection():
    """Crea una conexión a MySQL utilizando las credenciales del archivo .env."""
    # Usar las variables de entorno
    host = os.getenv('MYSQL_HOST')
    port = os.getenv('MYSQL_PORT')
    user = os.getenv('MYSQL_USER')
    password = os.getenv('MYSQL_PASSWORD')
    database = os.getenv('MYSQL_DB')

    # Conectar a MySQL utilizando las variables de entorno
    connection = mysql.connector.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database
    )

    print(f'Conectando a {database} en {host}:{port} como {user}')
    return connection
