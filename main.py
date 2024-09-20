
from app.services.redis_service import RedisService
from app.services.script_service import ScriptService

def main():
    redis_service = RedisService()
    script_service = ScriptService(redis_service)

    print("Esperando scripts...")
    while True:
        script_data = redis_service.get_next_script()
        if script_data:
            script_id, script_content = script_data
            print(f"Procesando script {script_id} con contenido: {script_content}")
            script_service.process_script(script_content, script_id)

if __name__ == "__main__":
    main()
