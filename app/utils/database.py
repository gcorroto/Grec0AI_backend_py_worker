import mysql.connector
import os
from dotenv import load_dotenv

# Cargar las variables desde el archivo .env
load_dotenv()

def get_db_connection():
    """Crea una conexión a MySQL utilizando las credenciales del archivo .env."""
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DB")
    )
