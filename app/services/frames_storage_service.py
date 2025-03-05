import os
import time
import uuid
import subprocess
import glob
from app.services.storage_service import StorageService

SCRIPTS_DIR = os.path.abspath("/scripts")
os.makedirs(SCRIPTS_DIR, exist_ok=True)

class FramesStorageService:
    def __init__(self, redis_service):
        self.redis_service = redis_service
        self.storage_service = StorageService()

    def process_video_to_frames(self, script_content, script_id, video_id):
        """
        1. Reemplaza los placeholders en el script con los nombres dinámicos.
        2. Descarga el video de MySQL y lo guarda como input_{unique_id}.mp4.
        3. Ejecuta el script en un contenedor Docker (imagen 'py-graph') para extraer los frames.
        4. Almacena cada captura generada y notifica en Redis.
        """
        # Actualizar el estado a "in_progress"
        self.redis_service.update_status(script_id, 'in_progress')
        current_dir = os.getcwd()
        unique_id = f"{script_id}_{int(time.time())}_{uuid.uuid4().hex}"
        
        # Definir nombres para el video de entrada y el patrón de salida de los frames
        input_video_name = f"input_{unique_id}"  # sin extensión
        output_pattern = f"frames_{unique_id}_%04d"  # Se generarán archivos: frames_<unique>_0001.png, etc.
        
        input_video_path = os.path.join(SCRIPTS_DIR, f"{input_video_name}.mp4")
        
        # Reemplazar los placeholders en el script
        script_content = script_content.replace("{{input_name}}", input_video_name)\
                                       .replace("{{output_pattern}}", f"frames_{unique_id}_%04d")
        
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
                'localhost:5000/py-audio',  # Imagen Docker que contiene Python y FFmpeg
                'python', f'/scripts/{script_file_name}'
            ], capture_output=True, text=True, check=True)
            
            print(f"Script ejecutado con éxito: {result.stdout}")
            
            # Buscar todos los frames generados
            frame_pattern = os.path.join(SCRIPTS_DIR, f"frames_{unique_id}_*.png")
            frame_files = sorted(glob.glob(frame_pattern))
            
            if frame_files:
                file_ids = []
                for frame in frame_files:
                    # Subir cada frame (se asume que save_file_to_mysql acepta un segundo parámetro para el tipo, por ejemplo, 'image')
                    file_id = self.storage_service.save_file_to_mysql(frame, 'image')
                    file_ids.append(file_id)
                    os.remove(frame)  # Borrar la imagen después de subirla
                self.redis_service.push_result(script_id, f"file_ids:{file_ids}")
            else:
                self.redis_service.push_result(script_id, f"No se encontraron capturas. {result.stdout}")
            
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
