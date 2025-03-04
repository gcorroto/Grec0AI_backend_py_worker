import os
import time
import uuid
import subprocess
from app.services.storage_service import StorageService

# Directorio para trabajar con los scripts y archivos
SCRIPTS_DIR = os.path.abspath("/scripts")
os.makedirs(SCRIPTS_DIR, exist_ok=True)

class VideoAudioService:
    def __init__(self, redis_service):
        self.redis_service = redis_service
        self.storage_service = StorageService()

    def process_video_conversion(self, script_content, script_id, video_id):
        # Actualizar el estado a "in_progress"
        self.redis_service.update_status(script_id, 'in_progress')
        current_dir = os.getcwd()
        unique_id = f"{script_id}_{int(time.time())}_{uuid.uuid4().hex}"
        
        # Definir rutas para el video de entrada y el audio de salida
        input_video_path = os.path.join(current_dir, "scripts", f"input_{unique_id}.mp4")
        output_audio_path = os.path.join(current_dir, "scripts", f"output_{unique_id}.mp3")

        # 1. Obtener el video desde MySQL mediante el video_id
        try:
            video_bytes = self.storage_service.get_file_from_mysql(video_id)
            with open(input_video_path, 'wb') as f:
                f.write(video_bytes)
            print(f"Video guardado en {input_video_path}")
        except Exception as e:
            error_message = f"Error al obtener video con ID {video_id}: {str(e)}"
            print(error_message)
            self.redis_service.push_result(script_id, error_message)
            self.redis_service.update_status(script_id, 'failed')
            return

        # 2. Ejecutar FFmpeg en Docker para convertir el video a audio (MP3)
        try:
            result = subprocess.run([
                'docker', 'run', '--rm',
                '-v', f'{current_dir}/scripts:/scripts',
                '-w', '/scripts',
                'localhost:5000/py-ai-scripter',  # Imagen Docker que incluye FFmpeg
                'ffmpeg',
                '-i', f'/scripts/{os.path.basename(input_video_path)}',
                '-vn',             # Ignorar el video
                '-ab', '192k',     # Bitrate del audio
                '-y',              # Sobrescribir el archivo de salida sin preguntar
                f'/scripts/{os.path.basename(output_audio_path)}'
            ], capture_output=True, text=True, check=True)

            print(f"Conversión ejecutada con éxito: {result.stdout}")

            # 3. Verificar si se generó el archivo de audio
            if os.path.exists(output_audio_path):
                # Subir el archivo de audio a MySQL y obtener un ID
                file_id = self.storage_service.save_file_to_mysql(output_audio_path)
                self.redis_service.push_result(script_id, f"Audio MP3 guardado con ID: {file_id}")
                os.remove(output_audio_path)
            else:
                self.redis_service.push_result(script_id, result.stdout)

            # Limpiar: eliminar el video de entrada
            os.remove(input_video_path)
            self.redis_service.update_status(script_id, 'completed')
        except subprocess.CalledProcessError as e:
            error_message = f"Error al convertir el video a audio: {e.stderr}"
            print(error_message)
            self.redis_service.push_result(script_id, error_message)
            self.redis_service.update_status(script_id, 'failed')
