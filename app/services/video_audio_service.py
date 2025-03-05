import os
import time
import uuid
import subprocess
from app.services.storage_service import StorageService

SCRIPTS_DIR = os.path.abspath("/scripts")
os.makedirs(SCRIPTS_DIR, exist_ok=True)

class VideoAudioService:
    def __init__(self, redis_service):
        self.redis_service = redis_service
        self.storage_service = StorageService()

    def process_video_conversion(self, script_content, script_id, video_id):
        """
        1. Crea un archivo con el script Python (script_content).
        2. Descarga el video de MySQL y lo guarda como input_{unique_id}.mp4.
        3. Lanza el contenedor Docker para ejecutar ese script, que hará la conversión a output_{unique_id}.mp3.
        4. Sube el MP3 resultante a MySQL y notifica en Redis.
        """
        # 1) Actualizar el estado a "in_progress"
        self.redis_service.update_status(script_id, 'in_progress')

        current_dir = os.getcwd()
        unique_id = f"{script_id}_{int(time.time())}_{uuid.uuid4().hex}"

         # Definir nombres para el video de entrada y el audio de salida
        input_video_name = f"input_{unique_id}"  # sin extensión
        output_audio_name = f"output_{unique_id}"  # sin extensión
        
        input_video_path = os.path.join(SCRIPTS_DIR, f"{input_video_name}.mp4")
        output_audio_path = os.path.join(SCRIPTS_DIR, f"{output_audio_name}.mp3")
        
        # Reemplazar placeholders en el script_content
        script_content = script_content.replace("{{input_name}}", input_video_name)\
                                       .replace("{{output_name}}", output_audio_name)

        # 2) Crear un archivo con el contenido del script
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

        # 3) Obtener el video desde MySQL
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
            # Limpieza del script
            if os.path.exists(script_path):
                os.remove(script_path)
            return

        # 4) Ejecutar el script dentro del contenedor Docker
        try:
            result = subprocess.run([
                'docker', 'run', '--rm',
                '-v', f'{SCRIPTS_DIR}:/scripts',
                '-w', '/scripts',
                'localhost:5000/py-audio',  # Imagen Docker que incluye Python y FFmpeg
                'python', f'/scripts/{script_file_name}'
            ], capture_output=True, text=True, check=True)

            print(f"Script ejecutado con éxito: {result.stdout}")

            # 5) Verificar si se generó el archivo de audio
            if os.path.exists(output_audio_path):
                # Subir el archivo de audio a MySQL y obtener un ID
                file_id = self.storage_service.save_file_to_mysql(output_audio_path, 'audio')
                self.redis_service.push_result(script_id, f"file_id:{file_id}")
                os.remove(output_audio_path)
            else:
                # Si no se encontró el output, mandamos el stdout como info
                self.redis_service.push_result(script_id, f"No se encontró {output_audio_name}. {result.stdout}")

            # Actualizar estado a completado
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
