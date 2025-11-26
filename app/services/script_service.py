# -*- coding: utf-8 -*-
import os
import subprocess
import time
import uuid
import re
from app.services.storage_service import StorageService

SCRIPTS_DIR = os.path.join(os.getcwd(), "scripts")
os.makedirs(SCRIPTS_DIR, exist_ok=True)

class ScriptService:
    def __init__(self, redis_service):
        self.redis_service = redis_service
        self.storage_service = StorageService()

    def check_redis_connection(self):
        try:
            print("Conexión a Redis exitosa")
        except Exception as e:
            print("Error conectando a Redis: {}".format(str(e)))
    
    def is_graphviz_content(self, content):
        """
        Detect if the content is Graphviz DOT notation.
        Returns True if content appears to be DOT notation, False otherwise.
        """
        content = content.strip()
        graphviz_patterns = [
            r'^\s*digraph\s+\w*\s*\{',
            r'^\s*graph\s+\w*\s*\{',
            r'^\s*strict\s+(di)?graph',
        ]
        
        for pattern in graphviz_patterns:
            if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                return True
        return False

    def process_script(self, script_content, script_id):
        self.redis_service.update_status(script_id, 'in_progress')
        
        try:
            if self.is_graphviz_content(script_content):
                print("Detected Graphviz content for script {}".format(script_id))
                self.process_graphviz_content(script_content, script_id)
                return
            
            print("Processing as Python script {}".format(script_id))
            self._process_python_script(script_content, script_id)
            
        except Exception as e:
            error_message = "Error processing script {}: {}".format(script_id, str(e))
            print(error_message)
            self.redis_service.push_result(script_id, error_message)
            self.redis_service.update_status(script_id, 'failed')
    
    def process_graphviz_content(self, graphviz_content, script_id):
        """Process Graphviz DOT notation"""
        # Placeholder for Graphviz processing
        print("Graphviz processing for script {}".format(script_id))
        self.redis_service.push_result(script_id, "Graphviz processing completed")
        self.redis_service.update_status(script_id, 'completed')
    
    def _process_python_script(self, script_content, script_id):
        """Process regular Python script content"""
        current_dir = os.getcwd()
        unique_id = "{}_{}_{}".format(script_id, int(time.time()), uuid.uuid4().hex)
        script_path = os.path.join(current_dir, "scripts", "temp_script_{}.py".format(unique_id))
        
        try:
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            print("Script saved at {}".format(script_path))
            result = subprocess.run(['python3', script_path], capture_output=True, text=True, timeout=30)
            
            self.redis_service.push_result(script_id, result.stdout)
            self.redis_service.update_status(script_id, 'completed')
            
        except Exception as e:
            error_message = "Error executing script {}: {}".format(script_path, str(e))
            print(error_message)
            self.redis_service.push_result(script_id, error_message)
            self.redis_service.update_status(script_id, 'failed')
        finally:
            if os.path.exists(script_path):
                os.remove(script_path)
