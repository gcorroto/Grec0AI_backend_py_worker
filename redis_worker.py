# import redis
# import subprocess
# import os
# import time
# import uuid

# # Conectar con Redis
# r = redis.StrictRedis(host='redis', port=6379, db=0)  # 'redis' es el nombre del servicio Redis en Docker Compose

# SCRIPTS_DIR = "/scripts"
# os.makedirs(SCRIPTS_DIR, exist_ok=True)

# def process_script(script_content, script_id):
#     r.set(f"script_status_{script_id}", "in_progress")
#     unique_id = f"{script_id}_{int(time.time())}_{uuid.uuid4().hex}"
#     script_path = f"{SCRIPTS_DIR}/temp_script_{unique_id}.py"
    
#     # Guardar el script
#     with open(script_path, 'w') as script_file:
#         script_file.write(script_content)

#     # Ejecutar el script en Docker
#     try:
#         result = subprocess.run([
#             'docker', 'run', '--rm',
#             '-v', f'{SCRIPTS_DIR}:/scripts',
#             'localhost:5000/py-ai-scripter'
#         ], capture_output=True, text=True, check=True)

#         r.rpush(f"results_queue_{script_id}", result.stdout)
#         r.set(f"script_status_{script_id}", "completed")

#     except subprocess.CalledProcessError as e:
#         error_message = f"Error al ejecutar el script {script_path}: {str(e)}"
#         r.rpush(f"results_queue_{script_id}", error_message)
#         r.set(f"script_status_{script_id}", "failed")

# def main():
#     print("Esperando scripts...")
#     while True:
#         script_data = r.blpop("scripts_queue")[1].decode("utf-8")
#         script_id, script_content = script_data.split(":", 1)
#         process_script(script_content, script_id)

# if __name__ == "__main__":
#     main()
