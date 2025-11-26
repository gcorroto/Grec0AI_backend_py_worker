# -*- coding: utf-8 -*-
import os
import subprocess
import time
import uuid
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
        unique_id = "{}_{}_{}".format(script_id, int(time.time()), uuid.uuid4().hex)
        
        # Definir nombres para el video de entrada y el patrón de salida de los frames
        input_video_name = "input_{}".format(unique_id)
        output_pattern = "frames_{}_%04d".format(unique_id)
        
        input_video_path = os.path.join(SCRIPTS_DIR, "{}.mp4".format(input_video_name))
        
        # Reemplazar los placeholders en el script
        script_content = script_content.replace("{{input_name}}", input_video_name)\
                                       .replace("{{output_pattern}}", "frames_{}_%04d".format(unique_id))
        
        # Guardar el script modificado en un archivo temporal
        script_file_name = "temp_script_{}.py".format(unique_id)
        script_path = os.path.join(SCRIPTS_DIR, script_file_name)
        
        try:
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            print("Script guardado en {}".format(script_path))
        except Exception as e:
            error_message = "Error al guardar el script: {}".format(str(e))
            print(error_message)
            self.redis_service.push_result(script_id, error_message)
            self.redis_service.update_status(script_id, 'failed')
            return

        # Descargar el video desde MySQL
        try:
            video_data = self.storage_service.get_video_from_mysql(video_id)
            with open(input_video_path, 'wb') as f:
                f.write(video_data)
            print("Video guardado en {}".format(input_video_path))
        except Exception as e:
            error_message = "Error al obtener video con ID {}: {}".format(video_id, str(e))
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
                '-v', '{}:/scripts'.format(SCRIPTS_DIR),
                '-w', '/scripts',
                'localhost:5000/py-graph',
                'python', '/scripts/{}'.format(script_file_name)
            ], capture_output=True, text=True, check=True)
            
            print("Script ejecutado con éxito")
            
            # Buscar todos los frames generados
            frame_pattern = os.path.join(SCRIPTS_DIR, "frames_{}_*.png".format(unique_id))
            frame_files = sorted(glob.glob(frame_pattern))
            
            if frame_files:
                file_ids = []
                for frame in frame_files:
                    file_id = self.storage_service.save_file_to_mysql(frame, 'image')
                    file_ids.append(file_id)
                    os.remove(frame)
                self.redis_service.push_result(script_id, "file_ids:{}".format(",".join(map(str, file_ids))))
            else:
                self.redis_service.push_result(script_id, "No se encontraron capturas. {}".format(result.stdout))
            
            self.redis_service.update_status(script_id, 'completed')
        except subprocess.CalledProcessError as e:
            error_message = "Error al ejecutar el script: {}".format(e.stderr)
            print(error_message)
            self.redis_service.push_result(script_id, error_message)
            self.redis_service.update_status(script_id, 'failed')
        finally:
            if os.path.exists(input_video_path):
                os.remove(input_video_path)
            if os.path.exists(script_path):
                os.remove(script_path)
