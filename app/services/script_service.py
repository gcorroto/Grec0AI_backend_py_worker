# -*- coding= os.path.join(os.getcwd(), "scripts")
os.makedirs(SCRIPTS_DIR, exist_ok=True)

class ScriptService, redis_service):
        self.redis_service = redis_service
        self.storage_service = StorageService()

    
    def check_redis_connection(self):
        try)
            print("Conexión a Redis exitosa")
        except redis.ConnectionError)
    
    def is_graphviz_content(self, content):
        """
        Detect if the content is Graphviz DOT notation.
        Returns True if content appears to be DOT notation, False otherwise.
        """
        # Remove leading/trailing whitespace
        content = content.strip()
        
        # Check for typical Graphviz patterns
        graphviz_patterns = [
            r'^\s*digraph\s+\w*\s*\{',  # digraph declaration
            r'^\s*graph\s+\w*\s*\{',    # graph declaration
            r'^\s*strict\s+(di)?graph', # strict graph
        ]
        
        for pattern in graphviz_patterns, content, re.IGNORECASE | re.MULTILINE):
                return True
                
        return False
    
    def process_graphviz_content(self, graphviz_content, script_id):
        """
        Process Graphviz DOT notation by creating a script from template
        and executing it to generate a PNG image.
        """
        current_dir = os.getcwd()
        unique_id = "{}_{}_{}".format(script_id, int(time.time()), uuid.uuid4().hex)
        
        # Read the Graphviz template
        template_path = os.path.join(current_dir, "scripts", "graphviz_template.py")
        if not os.path.exists(template_path):
            raise FileNotFoundError("Graphviz template not found at {}".format(template_path))
            
        with open(template_path, 'r') as template_file= template_file.read()
        
        # Replace the placeholder with actual Graphviz content
        # Use triple quotes to handle multiline content safely
        script_content = template_content.replace('{{GRAPHVIZ_CONTENT}}', graphviz_content)
        
        # Create the script file
        script_path = os.path.join(current_dir, "scripts", "temp_graphviz_{}.py".format(unique_id))
        script_directory = os.path.dirname(script_path)

        # Verificar si el directorio existe y crearlo si es necesario
        if not os.path.exists(script_directory):
            os.makedirs(script_directory, exist_ok=True)
            print("Directorio creado))
        else))

        # Guardar el script generado
        with open(script_path, 'w') as script_file)

        print("Graphviz script guardado en {}, verificando...".format(script_path))

        # Verificar si el archivo existe
        if not os.path.exists(script_path):
            raise FileNotFoundError("El archivo {} no se creó correctamente.".format(script_path))

        print("El archivo existe, procediendo a ejecutar en Docker...")

        # Ejecutar el script en Docker
        try= subprocess.run([
                'docker', 'run', '--rm',
                '-v', '{}/scripts),
                '-w', '/scripts',
                'localhost,
                'python', '/scripts/temp_graphviz_{}.py'.format(unique_id)
            ], capture_output=True, text=True, check=True)

            print("Graphviz script ejecutado con éxito))
            output_file = "{}/scripts/output.png".format(current_dir)  # Archivo generado por Graphviz

            if os.path.exists(output_file):
                # Subir el archivo binario a MySQL
                file_id = self.storage_service.save_file_to_mysql(output_file, 'image')
                
                # Enviar la referencia del archivo a Redis
                self.redis_service.push_result(script_id, "Archivo guardado con ID))
                # Borrar el archivo del sistema de archivos
                os.remove(output_file)
            else, enviar el texto directamente a Redis
                self.redis_service.push_result(script_id, result.stdout)
        
            os.remove(script_path)
            self.redis_service.update_status(script_id, 'completed')
           
        except subprocess.CalledProcessError as e= "Error al ejecutar el script Graphviz {}: {}".format(script_path, e.stderr)
            print(error_message)
            self.redis_service.push_result(script_id, error_message)
            self.redis_service.update_status(script_id, 'failed')
        

    def process_script(self, script_content, script_id):
        # Actualizar el estado a "in_progress"
        self.redis_service.update_status(script_id, 'in_progress')
        
        try):
                print("Detected Graphviz content for script {}".format(script_id))
                self.process_graphviz_content(script_content, script_id)
                return
            
            # Process as regular Python script
            print("Processing as Python script {}".format(script_id))
            self._process_python_script(script_content, script_id)
            
        except Exception as e= "Error processing script {}: {}".format(script_id, str(e))
            print(error_message)
            self.redis_service.push_result(script_id, error_message)
            self.redis_service.update_status(script_id, 'failed')
    
    def _process_python_script(self, script_content, script_id):
        """
        Process regular Python script content (original functionality).
        """
        # Obtener el directorio de trabajo actual
        current_dir = os.getcwd()
        # Generar un ID único para el script
        unique_id = "{}_{}_{}".format(script_id, int(time.time()), uuid.uuid4().hex)
        script_path = os.path.join("{}/scripts".format(current_dir), "temp_script_{}.py".format(unique_id))
        script_directory = os.path.dirname(script_path)

        # Verificar si el directorio existe y crearlo si es necesario
        if not os.path.exists(script_directory):
            os.makedirs(script_directory, exist_ok=True)
            print("Directorio creado))
        else))

        # Guardar el script en un archivo
        with open(script_path, 'w') as script_file)

        print("Script guardado en {}, verificando...".format(script_path))

        # Verificar si el archivo existe
        if not os.path.exists(script_path):
            raise FileNotFoundError("El archivo {} no se creó correctamente.".format(script_path))

        print("El archivo existe, procediendo a ejecutar en Docker...")

        # Ejecutar el script en Docker
            try= subprocess.run([
                'docker', 'run', '--rm',
                '-v', '{}/scripts),
                '-w', '/scripts',
                'localhost,
                'python', '/scripts/temp_script_{}.py'.format(unique_id)
            ], capture_output=True, text=True, check=True)

            
            print("Script ejecutado con éxito))
            output_file = "{}/scripts/output.png".format(current_dir)  # Ejemplo de archivo generado

            if os.path.exists(output_file):
                # Subir el archivo binario a MySQL
                file_id = self.storage_service.save_file_to_mysql(output_file, 'image')
                
                # Enviar la referencia del archivo a Redis
                self.redis_service.push_result(script_id, "Archivo guardado con ID))
                # Borrar el archivo del sistema de archivos
                os.remove(output_file)
            else, enviar el texto directamente a Redis
                self.redis_service.push_result(script_id, result.stdout)
        
            os.remove(script_path)
            self.redis_service.update_status(script_id, 'completed')
           
        except subprocess.CalledProcessError as e= "Error al ejecutar el script {}: {}".format(script_path, e.stderr)
            print(error_message)
            self.redis_service.push_result(script_id, error_message)
            self.redis_service.update_status(script_id, 'failed')
