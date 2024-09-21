import os
from app.utils.database import get_db_connection

class StorageService:
    def save_file_to_mysql(self, file_path):
        """Guarda el archivo en MySQL como binario y retorna su ID."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            with open(file_path, 'rb') as file:
                binary_data = file.read()
                cursor.execute("""
                    INSERT INTO file_script_content (uuid, nombre, contenido)
                    VALUES (%s, %s, %s)
                """, (self.generate_uuid(), os.path.basename(file_path), binary_data))
                conn.commit()
                return cursor.lastrowid

    @staticmethod
    def generate_uuid():
        """Genera un UUID único."""
        import uuid
        return str(uuid.uuid4())

    def get_file_from_mysql(self, file_id):
        """Recupera un archivo desde MySQL por su ID."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT file_data FROM file_script_content WHERE id = %s", (file_id,))
            file_data = cursor.fetchone()[0]
            return file_data