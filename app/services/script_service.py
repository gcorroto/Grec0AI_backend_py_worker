import os
import time
import uuid
import redis
import subprocess
from app.services.storage_service import StorageService

SCRIPTS_DIR = "/scripts"
os.makedirs(SCRIPTS_DIR, exist_ok=True)

class ScriptService:
    def __init__(self, redis_service):
        self.redis_service = redis_service
        self.storage_service = StorageService()

    
    def check_redis_connection(self):
        try:
            self.redis_service.r.ping()
            print("Conexión a Redis exitosa")
        except redis.ConnectionError:
            print("Error al conectar a Redis")
        

    def process_script(self, script_content, script_id):
        # Actualizar el estado a "in_progress"
        self.redis_service.update_status(script_id, "in_progress")
        
        # Generar un ID único para el script
        unique_id = f"{script_id}_{int(time.time())}_{uuid.uuid4().hex}"
        script_path = f"{SCRIPTS_DIR}/temp_script_{unique_id}.py"
        
        # Guardar el script en un archivo
        with open(script_path, 'w') as script_file:
            script_file.write(script_content)

        print(f"Script guardado en {script_path}, ejecutando...")

        # Ejecutar el script en Docker
        try:
            result = subprocess.run([
                'docker', 'run', '--rm',
                '-v', f'{SCRIPTS_DIR}:/scripts',
                'localhost:5000/py-ai-scripter',
                f'python /scripts/temp_script_{unique_id}.py'
            ], capture_output=True, text=True, check=True)
            
            print(f"Script ejecutado con éxito: {result.stdout}")
            output_file = f"/scripts/output_{unique_id}.png"  # Ejemplo de archivo generado

            if os.path.exists(output_file):
                # Subir el archivo binario a MySQL
                file_id = self.storage_service.save_file_to_mysql(output_file)
                
                # Enviar la referencia del archivo a Redis
                self.redis_service.push_result(script_id, f"Archivo guardado con ID: {file_id}")
            else:
                # Si no hay archivo, enviar el texto directamente a Redis
                self.redis_service.push_result(script_id, result.stdout)

            self.redis_service.update_status(script_id, "completed")

        except subprocess.CalledProcessError as e:
            # Manejo de errores
            error_message = f"Error al ejecutar el script {script_path}: {e.stderr}"
            print(error_message)
            self.redis_service.push_result(script_id, error_message)
            self.redis_service.update_status(script_id, "failed")
