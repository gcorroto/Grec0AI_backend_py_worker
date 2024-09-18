import redis
import subprocess
import os
import time
import uuid

# Conectar con Redis
r = redis.StrictRedis(host='redis', port=6379, db=0)  # 'redis' es el nombre del servicio Redis en Docker Compose

SCRIPTS_DIR = "/scripts"
os.makedirs(SCRIPTS_DIR, exist_ok=True)

def process_script(script_content, script_id):
    # Actualizar el estado del script en Redis
    r.set(f"script_status_{script_id}", "in_progress")
    
    # Generar un ID único para el script
    unique_id = f"{script_id}_{int(time.time())}_{uuid.uuid4().hex}"
    script_path = f"{SCRIPTS_DIR}/temp_script_{unique_id}.py"
    
    # Guardar el script en un archivo temporal
    with open(script_path, 'w') as script_file:
        script_file.write(script_content)
    
    print(f"Script guardado en {script_path}, ejecutando...")

    # Ejecutar el script en un contenedor Docker
    try:
        result = subprocess.run([
            'docker', 'run', '--rm',
            '-v', f'{SCRIPTS_DIR}:/scripts',
            'localhost:5000/py-ai-scripter',  # Imagen de Docker a ejecutar
            f"python /scripts/temp_script_{unique_id}.py"
        ], capture_output=True, text=True, check=True)
        
        # Log de la ejecución
        print(f"Script {script_id} ejecutado con éxito.")
        print(f"Resultado: {result.stdout}")
        
        # Publicar el resultado en Redis
        r.rpush(f"results_queue_{script_id}", result.stdout)
        r.set(f"script_status_{script_id}", "completed")
    
    except subprocess.CalledProcessError as e:
        # Captura de errores durante la ejecución del script
        error_message = f"Error al ejecutar el script {script_path}: {e.stderr}"
        print(error_message)
        
        # Publicar el error en Redis
        r.rpush(f"results_queue_{script_id}", error_message)
        r.set(f"script_status_{script_id}", "failed")

def main():
    print("Esperando scripts...")
    while True:
        # Leer el próximo script de la cola de Redis
        script_data = r.blpop("scripts_queue")[1].decode("utf-8")
        
        # Separar el script_id del contenido del script
        script_id, script_content = script_data.split(":", 1)
        
        print(f"Script recibido con ID: {script_id}")
        
        # Procesar el script
        process_script(script_content, script_id)

if __name__ == "__main__":
    main()
