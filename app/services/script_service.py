import os
import time
import uuid
import redis
import subprocess
from app.services.storage_service import StorageService




SCRIPTS_DIR = os.path.abspath("/scripts")
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
        self.redis_service.update_status(script_id, 'in_progress')
        # Obtener el directorio de trabajo actual
        current_dir = os.getcwd()
        # Generar un ID único para el script
        unique_id = f"{script_id}_{int(time.time())}_{uuid.uuid4().hex}"
        script_path = os.path.join(f"{current_dir}/scripts", f"temp_script_{unique_id}.py")
        script_directory = os.path.dirname(script_path)

        # Verificar si el directorio existe y crearlo si es necesario
        if not os.path.exists(script_directory):
            os.makedirs(script_directory, exist_ok=True)
            print(f"Directorio creado: {script_directory}")
        else:
            print(f"El directorio ya existe: {script_directory}")

        # Guardar el script en un archivo
        with open(script_path, 'w') as script_file:
            script_file.write(script_content)

        print(f"Script guardado en {script_path}, verificando...")

        # Verificar si el archivo existe
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"El archivo {script_path} no se creó correctamente.")

        print("El archivo existe, procediendo a ejecutar en Docker...")

        # Ejecutar el script en Docker
        try:
            result = subprocess.run([
                'docker', 'run', '--rm',
                '-v', f'{current_dir}/scripts:/scripts',
                '-w', '/scripts',
                'localhost:5000/py-ai-scripter',
                'python', f'/scripts/temp_script_{unique_id}.py'
            ], capture_output=True, text=True, check=True)

            
            print(f"Script ejecutado con éxito: {result.stdout}")
            output_file = f"{current_dir}/scripts/output.png"  # Ejemplo de archivo generado

            if os.path.exists(output_file):
                # Subir el archivo binario a MySQL
                file_id = self.storage_service.save_file_to_mysql(output_file)
                
                # Enviar la referencia del archivo a Redis
                self.redis_service.push_result(script_id, f"Archivo guardado con ID: {file_id}")
                # Borrar el archivo del sistema de archivos
                os.remove(output_file)
            else:
                # Si no hay archivo, enviar el texto directamente a Redis
                self.redis_service.push_result(script_id, result.stdout)
        
            os.remove(script_path)
            self.redis_service.update_status(script_id, 'completed')
           
        except subprocess.CalledProcessError as e:
            # Manejo de errores
            error_message = f"Error al ejecutar el script {script_path}: {e.stderr}"
            print(error_message)
            self.redis_service.push_result(script_id, error_message)
            self.redis_service.update_status(script_id, 'failed')
