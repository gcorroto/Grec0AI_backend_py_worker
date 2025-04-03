import redis

class RedisService:
    def __init__(self):
        self.r = redis.StrictRedis(host='127.0.0.1', port=6379, db=0)  # Configuración de Redis

    def get_next_script(self):
        """Obtiene el siguiente script de la cola en Redis (flujo original)."""
        script_data = self.r.blpop("scripts_queue", timeout=0)
        if script_data:
            decoded_data = script_data[1].decode("utf-8")
            return decoded_data.split(":", 1)
        return None

    def get_next_video_script(self):
        """
        Obtiene el siguiente mensaje de la cola en Redis para conversión de video.
        Se espera el formato: script_id:script_content:video_id
        """
        script_data = self.r.blpop("video_scripts_queue", timeout=0)
        if script_data:
            decoded_data = script_data[1].decode("utf-8")
            # Separa en 3 partes (separadas por dos puntos)
            parts = decoded_data.split(":", 2)
            if len(parts) == 3:
                return parts
        return None

    def get_next_frames_script(self):
        """
        Obtiene el siguiente mensaje de la cola en Redis para conversión de video.
        Se espera el formato: script_id:script_content:video_id
        """
        script_data = self.r.blpop("frames_scripts_queue", timeout=0)
        if script_data:
            decoded_data = script_data[1].decode("utf-8")
            # Separa en 3 partes (separadas por dos puntos)
            parts = decoded_data.split(":", 2)
            if len(parts) == 3:
                return parts
        return None
    def get_next_metadata_script(self):
        """
        Obtiene el siguiente mensaje de la cola en Redis para la extraccion de metadatos.
        Se espera el formato: script_id:script_content:video_id
        """
        script_data = self.r.blpop("metadata_scripts_queue", timeout=0)
        if script_data:
            decoded_data = script_data[1].decode("utf-8")
            # Separa en 3 partes (separadas por dos puntos)
            parts = decoded_data.split(":", 2)
            if len(parts) == 3:
                return parts
        return None

    def update_status(self, script_id, status):
        """Actualiza el estado del script en Redis."""
        key = f"script_status_{script_id}"
        if self.r.exists(key):
            key_type = self.r.type(key)
            if key_type != b'list':
                self.r.delete(key)
        self.r.rpush(key, status)

    def push_result(self, script_id, result):
        """Envía el resultado del script a Redis."""
        self.r.rpush(f"results_queue_{script_id}", result)
