# -*- coding: utf-8 -*-
import os
import uuid
from app.database import get_db_connection

class StorageService:
    def save_file_to_mysql(self, file_path, file_type):
        """Guarda el archivo en MySQL como binario y retorna su ID."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            with open(file_path, 'rb') as file:
                binary_data = file.read()
                cursor.execute("""
                    INSERT INTO file_script_content (uuid, nombre, contenido, type)
                    VALUES (%s, %s, %s, %s)
                """, (self.generate_uuid(), os.path.basename(file_path), binary_data, file_type))
                conn.commit()
                return cursor.lastrowid

    @staticmethod
    def generate_uuid():
        """Genera un UUID único."""
        return str(uuid.uuid4())

    def get_video_from_mysql(self, file_id):
        """Recupera y concatena los fragmentos de un video desde MySQL por su ID."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT fragment FROM file_content_video 
                WHERE video_id = %s 
                ORDER BY id ASC
            """, (file_id,))
            fragments = cursor.fetchall()

            if not fragments:
                return None
            
            video_data = b''.join([fragment[0] for fragment in fragments])
            return video_data