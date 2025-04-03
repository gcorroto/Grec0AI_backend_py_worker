import os
import time
import uuid
import subprocess
from app.services.storage_service import StorageService

SCRIPTS_DIR = os.path.abspath("/scripts")
os.makedirs(SCRIPTS_DIR, exist_ok=True)

class MetadataStorageService:
    def __init__(self, redis_service):
        self.redis_service = redis_service
        self.storage_service = StorageService()

    def process_video_metadata(self, script_content, script_id, video_id):
        """
        Proceso para extraer metadatos de un video:
        1. Reemplaza los placeholders en el script (por ejemplo, {{input_name}})
           con un nombre único para el archivo.
        2. Descarga el video desde MySQL y lo guarda como input_<unique_id>.mp4.
        3. Ejecuta el script en un contenedor Docker (que tenga Python y ffprobe) para extraer los metadatos.
        4. Envía el resultado (metadatos en formato JSON u otro) a Redis.
        """
        # Actualizar el estado a "in_progress"
        self.redis_service.update_status(script_id, 'in_progress')
        unique_id = f"{script_id}_{int(time.time())}_{uuid.uuid4().hex}"
        
        # Definir el nombre para el video de entrada (sin extensión)
        input_video_name = f"input_{unique_id}"
        input_video_path = os.path.join(SCRIPTS_DIR, f"{input_video_name}.mp4")
        
        # Reemplazar el placeholder en el script
        script_content = script_content.replace("{{input_name}}", input_video_name)
        
        # Guardar el script modificado en un archivo temporal
        script_file_name = f"temp_script_{unique_id}.py"
        script_path = os.path.join(SCRIPTS_DIR, script_file_name)
        
        try:
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            print(f"Script guardado en {script_path}")
        except Exception as e:
            error_message = f"Error al guardar el script: {str(e)}"
            print(error_message)
            self.redis_service.push_result(script_id, error_message)
            self.redis_service.update_status(script_id, 'failed')
            return
        
        # Descargar el video desde MySQL
        try:
            video_bytes = self.storage_service.get_video_from_mysql(video_id)
            with open(input_video_path, 'wb') as f:
                f.write(video_bytes)
            print(f"Video guardado en {input_video_path}")
        except Exception as e:
            error_message = f"Error al obtener video con ID {video_id}: {str(e)}"
            print(error_message)
            self.redis_service.push_result(script_id, error_message)
            self.redis_service.update_status(script_id, 'failed')
            if os.path.exists(script_path):
                os.remove(script_path)
            return
        
        # Ejecutar el script dentro del contenedor Docker
        try:
            result = subprocess.run([
                'docker', 'run', '--rm',
                '-v', f'{SCRIPTS_DIR}:/scripts',
                '-w', '/scripts',
                'localhost:5000/py-audio',  # Imagen Docker que incluye Python y ffprobe
                'python', f'/scripts/{script_file_name}'
            ], capture_output=True, text=True, check=True)
            
            print(f"Script ejecutado con éxito: {result.stdout}")
            # Enviar el resultado (metadatos extraídos) a Redis
            self.redis_service.push_result(script_id, result.stdout)
            self.redis_service.update_status(script_id, 'completed')
        except subprocess.CalledProcessError as e:
            error_message = f"Error al ejecutar el script: {e.stderr}"
            print(error_message)
            self.redis_service.push_result(script_id, error_message)
            self.redis_service.update_status(script_id, 'failed')
        finally:
            # Limpieza de archivos temporales
            if os.path.exists(input_video_path):
                os.remove(input_video_path)
            if os.path.exists(script_path):
                os.remove(script_path)
