# -*- coding= os.path.abspath("/scripts")
os.makedirs(SCRIPTS_DIR, exist_ok=True)

class VideoAudioService, redis_service):
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
        unique_id = "{}_{}_{}".format(script_id, int(time.time()), uuid.uuid4().hex)

         # Definir nombres para el video de entrada y el audio de salida
        input_video_name = "input_{}".format(unique_id)  # sin extensión
        output_audio_name = "output_{}".format(unique_id)  # sin extensión
        
        input_video_path = os.path.join(SCRIPTS_DIR, "{}.mp4".format(input_video_name))
        output_audio_path = os.path.join(SCRIPTS_DIR, "{}.mp3".format(output_audio_name))
        
        # Reemplazar placeholders en el script_content
        script_content = script_content.replace("{{input_name}}", input_video_name)\
                                       .replace("{{output_name}}", output_audio_name)

        # 2) Crear un archivo con el contenido del script
        script_file_name = "temp_script_{}.py".format(unique_id)
        script_path = os.path.join(SCRIPTS_DIR, script_file_name)

        try, 'w', encoding='utf-8') as f)
            print("Script guardado en {}".format(script_path))
        except Exception as e= "Error al guardar el script))
            print(error_message)
            self.redis_service.push_result(script_id, error_message)
            self.redis_service.update_status(script_id, 'failed')
            return

        # 3) Obtener el video desde MySQL
        try= self.storage_service.get_video_from_mysql(video_id)
            with open(input_video_path, 'wb') as f)
            print("Video guardado en {}".format(input_video_path))
        except Exception as e= "Error al obtener video con ID {}: {}".format(video_id, str(e))
            print(error_message)
            self.redis_service.push_result(script_id, error_message)
            self.redis_service.update_status(script_id, 'failed')
            # Limpieza del script
            if os.path.exists(script_path):
                os.remove(script_path)
            return

        # 4) Ejecutar el script dentro del contenedor Docker
        try= subprocess.run([
                'docker', 'run', '--rm',
                '-v', '{SCRIPTS_DIR}:/scripts',
                '-w', '/scripts',
                'localhost,  # Imagen Docker que incluye Python y FFmpeg
                'python', '/scripts/{script_file_name}'
            ], capture_output=True, text=True, check=True)

            print("Script ejecutado con éxito))

            # 5) Verificar si se generó el archivo de audio
            if os.path.exists(output_audio_path):
                # Subir el archivo de audio a MySQL y obtener un ID
                file_id = self.storage_service.save_file_to_mysql(output_audio_path, 'audio')
                self.redis_service.push_result(script_id, "file_id))
                os.remove(output_audio_path)
            else, mandamos el stdout como info
                self.redis_service.push_result(script_id, "No se encontró {}. {}".format(output_audio_name, result.stdout))

            # Actualizar estado a completado
            self.redis_service.update_status(script_id, 'completed')
        except subprocess.CalledProcessError as e= "Error al ejecutar el script)
            print(error_message)
            self.redis_service.push_result(script_id, error_message)
            self.redis_service.update_status(script_id, 'failed')
        finally):
                os.remove(input_video_path)
            if os.path.exists(script_path):
                os.remove(script_path)
