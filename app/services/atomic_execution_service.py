# -*- coding: utf-8 -*-
import subprocess
import json
import os
import sys
import base64
import time
import uuid

SCRIPTS_DIR = os.path.abspath("/scripts")
os.makedirs(SCRIPTS_DIR, exist_ok=True)

class AtomicExecutionService:
    def __init__(self, redis_service, storage_service):
        self.redis_service = redis_service
        self.storage_service = storage_service
    
    def process_atomic_step(self, step_token, step_number, encoded_code, container_type):
        """
        Procesa un paso atómico de ejecución GREC0AI ejecutando el código en un contenedor Docker
        
        Args:
            step_token: Token completo "traceToken:step:N"
            step_number: Número del paso
            encoded_code: Código Python en Base64
            container_type: "py-graph" o "py-audio"
        """
        trace_token = step_token.split(":step:")[0]
        
        # Debug: mostrar longitud del código codificado
        print("Longitud encoded_code: {} caracteres".format(len(encoded_code)))
        print("Primeros 50 chars: {}".format(encoded_code[:50]))
        
        # Decodificar código
        try:
            code = base64.b64decode(encoded_code).decode('utf-8')
        except Exception as e:
            error_msg = "Error decodificando código del paso {}: {}".format(step_number, str(e))
            print(error_msg)
            print("Encoded_code recibido: {}".format(encoded_code))
            self.redis_service.push_result("step_output_{}".format(step_token), error_msg)
            self.redis_service.update_status("step_status_{}".format(step_token), "FAILED")
            return
        
        # NO actualizar a EXECUTING aquí porque Java espera solo un valor final (SUCCESS o FAILED)
        print("→ Ejecutando paso {} de traza {} en contenedor {}".format(step_number, trace_token, container_type))
        
        # Generar nombre único para el script temporal
        unique_id = "{}_{}_{}_{}".format(trace_token, step_number, int(time.time()), uuid.uuid4().hex[:8])
        script_file_name = "atomic_step_{}.py".format(unique_id)
        script_path = os.path.join(SCRIPTS_DIR, script_file_name)
        
        # Guardar el código decodificado en un archivo temporal
        try:
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(code)
            print("Script guardado en {}".format(script_path))
            print("=== CÓDIGO A EJECUTAR ===")
            print(code)
            print("=== FIN CÓDIGO ===")
        except Exception as e:
            error_msg = "Error al guardar script del paso {}: {}".format(step_number, str(e))
            print(error_msg)
            self.redis_service.push_result("step_output_{}".format(step_token), error_msg)
            self.redis_service.update_status("step_status_{}".format(step_token), "FAILED")
            return
        
        # Determinar la imagen Docker según el tipo de contenedor
        docker_image = "localhost:5000/{}".format(container_type)
        
        # Ejecutar el script dentro del contenedor Docker
        try:
            result = subprocess.run([
                'docker', 'run', '--rm',
                '-v', '{}:/scripts'.format(SCRIPTS_DIR),
                '-w', '/scripts',
                docker_image,
                'python', '/scripts/{}'.format(script_file_name)
            ], capture_output=True, text=True, check=True, timeout=300)
            
            print("✓ Script ejecutado con éxito en contenedor {}".format(container_type))
            
            # Reportar resultados en Redis
            output_key = "step_output_{}".format(step_token)
            status_key = "step_status_{}".format(step_token)
            
            print("→ Escribiendo resultados en Redis:")
            print("   Output key: {}".format(output_key))
            print("   Status key: {}".format(status_key))
            
            # El output es la salida estándar del script
            output = result.stdout if result.stdout else "Ejecución completada sin salida"
            self.redis_service.push_result(output_key, output)
            self.redis_service.update_status(status_key, "SUCCESS")
            
            print("✓ Paso {} completado exitosamente".format(step_number))
            print("✓ Resultados escritos en Redis")
            
        except subprocess.TimeoutExpired:
            error_msg = "Timeout ejecutando paso {}: superó 300 segundos".format(step_number)
            print("✗ {}".format(error_msg))
            self.redis_service.push_result("step_output_{}".format(step_token), error_msg)
            self.redis_service.update_status("step_status_{}".format(step_token), "FAILED")
        except subprocess.CalledProcessError as e:
            error_msg = "Error ejecutando paso {} en contenedor {}:\nSTDOUT:\n{}\nSTDERR:\n{}".format(
                step_number, container_type, e.stdout, e.stderr
            )
            print("✗ {}".format(error_msg))
            self.redis_service.push_result("step_output_{}".format(step_token), error_msg)
            self.redis_service.update_status("step_status_{}".format(step_token), "FAILED")
        except Exception as e:
            error_msg = "Error inesperado en paso {}: {}".format(step_number, str(e))
            print("✗ {}".format(error_msg))
            self.redis_service.push_result("step_output_{}".format(step_token), error_msg)
            self.redis_service.update_status("step_status_{}".format(step_token), "FAILED")
        finally:
            # Limpiar el archivo temporal
            if os.path.exists(script_path):
                os.remove(script_path)
                print("Script temporal eliminado: {}".format(script_path))


