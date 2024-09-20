import redis

class RedisService:
    def __init__(self):
        self.r = redis.StrictRedis(host='127.0.0.1', port=6379, db=0)  # Configuración de Redis

    def get_next_script(self):
        """Obtiene el siguiente script de la cola en Redis."""
        script_data = self.r.blpop("scripts_queue", timeout=0)
        if script_data:
            decoded_data = script_data[1].decode("utf-8")
            return decoded_data.split(":", 1)
        return None

    def update_status(self, script_id, status):
        """Actualiza el estado del script en Redis."""
        self.r.set(f"script_status_{script_id}", status)

    def push_result(self, script_id, result):
        """Envía el resultado del script a Redis."""
        self.r.rpush(f"results_queue_{script_id}", result)
