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
    
    def _find_generated_files(self, scripts_dir, script_name):
        """
        Busca archivos generados en el directorio de scripts, excluyendo el script temporal
        
        Args:
            scripts_dir: Directorio donde se ejecutó el script
            script_name: Nombre del script temporal a excluir
        
        Returns:
            Lista de rutas de archivos generados
        """
        generated_files = []
        try:
            for filename in os.listdir(scripts_dir):
                file_path = os.path.join(scripts_dir, filename)
                # Excluir el script temporal y directorios
                if filename != script_name and os.path.isfile(file_path):
                    # Excluir archivos .py (scripts)
                    if not filename.endswith('.py'):
                        generated_files.append(file_path)
                        print("   → Archivo detectado: {}".format(filename))
        except Exception as e:
            print("Error buscando archivos generados: {}".format(str(e)))
        
        return generated_files
    
    def _detect_file_type(self, file_path):
        """
        Detecta el tipo de archivo basándose en su extensión
        
        Args:
            file_path: Ruta del archivo
        
        Returns:
            Tipo de archivo como string ('image', 'audio', 'video', 'text', etc.)
        """
        extension = os.path.splitext(file_path)[1].lower()
        
        # Mapeo de extensiones a tipos
        image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp', '.ico']
        audio_extensions = ['.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac']
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv']
        text_extensions = ['.txt', '.log', '.md', '.json', '.xml', '.csv', '.tsv']
        document_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
        
        if extension in image_extensions:
            return 'image'
        elif extension in audio_extensions:
            return 'audio'
        elif extension in video_extensions:
            return 'video'
        elif extension in text_extensions:
            return 'text'
        elif extension in document_extensions:
            return 'document'
        else:
            return 'binary'  # Tipo genérico para archivos desconocidos
    
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
            
            # Buscar archivos generados en el directorio de scripts
            generated_files = self._find_generated_files(SCRIPTS_DIR, script_file_name)
            
            # Reportar resultados en Redis
            output_key = "step_output_{}".format(step_token)
            status_key = "step_status_{}".format(step_token)
            
            print("→ Escribiendo resultados en Redis:")
            print("   Output key: {}".format(output_key))
            print("   Status key: {}".format(status_key))
            
            # El output es la salida estándar del script
            output = result.stdout if result.stdout else "Ejecución completada sin salida"
            
            # Si hay archivos generados, guardarlos en la BD
            if generated_files:
                print("→ Archivos generados detectados: {}".format(generated_files))
                for file_path in generated_files:
                    try:
                        file_name = os.path.basename(file_path)
                        file_type = self._detect_file_type(file_path)
                        print("   → Guardando {} (tipo: {})".format(file_name, file_type))
                        
                        file_id = self.storage_service.save_file_to_mysql(file_path, file_type)
                        
                        # DEBUG: Verificar qué devolvió
                        if file_id is None:
                            print("   ✗ ERROR: save_file_to_mysql devolvió None")
                            import traceback
                            traceback.print_stack()
                        
                        output += "\n[ARCHIVO_GENERADO] {} (tipo: {}) -> ID: {}".format(file_name, file_type, file_id)
                        print("   ✓ Archivo {} guardado con ID: {}".format(file_name, file_id))
                        # Limpiar archivo después de guardarlo
                        os.remove(file_path)
                    except Exception as e:
                        print("   ✗ Error guardando archivo {}: {}".format(file_path, str(e)))
                        import traceback
                        traceback.print_exc()
            
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


