# -*- coding: utf-8 -*-
import subprocess
import json
import os
import sys
import base64
from io import StringIO
import contextlib

class AtomicExecutionService:
    def __init__(self, redis_service, storage_service):
        self.redis_service = redis_service
        self.storage_service = storage_service
        self.execution_contexts = {}  # trace_token -> namespace dict
    
    def process_atomic_step(self, step_token, step_number, encoded_code, container_type):
        """
        Procesa un paso atómico de ejecución GREC0AI
        
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
        
        # 1. Recuperar contexto de pasos previos
        context = self.execution_contexts.get(trace_token, {})
        
        # 2. Ejecutar código con contexto
        try:
            self.redis_service.update_status("step_status_{}".format(step_token), "EXECUTING")
            print("→ Ejecutando paso {} de traza {}".format(step_number, trace_token))
            
            result = self.execute_code_with_context(code, context, container_type)
            
            # 3. Actualizar contexto con nuevas variables
            self.execution_contexts[trace_token] = result['namespace']
            
            # 4. Reportar resultado
            output_key = "step_output_{}".format(step_token)
            context_key = "step_context_{}".format(step_token)
            status_key = "step_status_{}".format(step_token)
            
            print("→ Escribiendo resultados en Redis:")
            print("   Output key: {}".format(output_key))
            print("   Context key: {}".format(context_key))
            print("   Status key: {}".format(status_key))
            
            self.redis_service.push_result(output_key, result['output'])
            self.redis_service.push_result(context_key, json.dumps(result['namespace']))
            self.redis_service.update_status(status_key, "SUCCESS")
            
            print("✓ Paso {} completado exitosamente".format(step_number))
            print("✓ Resultados escritos en Redis")
            
        except Exception as e:
            error_msg = "Error en paso {}: {}".format(step_number, str(e))
            print("✗ {}".format(error_msg))
            self.redis_service.push_result("step_output_{}".format(step_token), error_msg)
            self.redis_service.update_status("step_status_{}".format(step_token), "FAILED")
    
    def execute_code_with_context(self, code, context, container_type):
        """
        Ejecuta código Python manteniendo el namespace entre pasos
        """
        # Crear namespace con el contexto previo
        exec_namespace = context.copy()
        
        # Agregar módulos básicos al namespace
        exec_namespace['__builtins__'] = __builtins__
        
        # Capturar stdout
        output_buffer = StringIO()
        
        with contextlib.redirect_stdout(output_buffer):
            try:
                # Ejecutar código en el namespace
                exec(code, exec_namespace)
            except Exception as e:
                # Capturar el error pero incluir el traceback
                import traceback
                error_details = traceback.format_exc()
                raise Exception("{}\n\nTraceback:\n{}".format(str(e), error_details))
        
        # Extraer solo variables nuevas (no built-ins, no imports de sistema)
        new_vars = {
            k: v for k, v in exec_namespace.items()
            if not k.startswith('__') and k not in ['json', 'os', 'sys', 'subprocess', 'builtins']
        }
        
        # Serializar variables para persistencia (solo tipos básicos)
        serializable_vars = self.serialize_namespace(new_vars)
        
        return {
            'output': output_buffer.getvalue(),
            'namespace': serializable_vars
        }
    
    def serialize_namespace(self, namespace):
        """Convierte namespace a tipos JSON-serializables"""
        serialized = {}
        for key, value in namespace.items():
            try:
                if isinstance(value, (str, int, float, bool, type(None))):
                    serialized[key] = value
                elif isinstance(value, (list, tuple)):
                    # Intentar serializar listas/tuplas
                    serialized[key] = list(value)
                elif isinstance(value, dict):
                    serialized[key] = value
                elif isinstance(value, bytes):
                    # Convertir bytes a base64 string
                    serialized[key] = base64.b64encode(value).decode('utf-8')
                else:
                    # Para objetos complejos, guardar representación string
                    serialized[key] = "<{}>".format(type(value).__name__)
            except Exception as e:
                print("Warning: No se pudo serializar variable '{}': {}".format(key, str(e)))
                serialized[key] = "<unserializable: {}>".format(type(value).__name__)
        
        return serialized
    
    def cleanup_context(self, trace_token):
        """Limpia el contexto de una traza completada"""
        if trace_token in self.execution_contexts:
            del self.execution_contexts[trace_token]
            print("Contexto de traza {} limpiado".format(trace_token))

