import threading
import time
from app.services.redis_service import RedisService
from app.services.script_service import ScriptService
from app.services.video_audio_service import VideoAudioService
from app.services.frames_storage_service import FramesStorageService

def script_worker(redis_service, script_service):
    print("Iniciando worker de scripts...")
    while True:
        # Escucha en la cola "scripts_queue"
        script_data = redis_service.get_next_script()
        if script_data:
            script_id, script_content = script_data
            print(f"Procesando script {script_id} con contenido: {script_content}")
            script_service.process_script(script_content, script_id)
        else:
            time.sleep(1)

def video_worker(redis_service, video_audio_service):
    print("Iniciando worker de conversión de video a audio...")
    while True:
        # Escucha en la cola "video_scripts_queue"
        video_script_data = redis_service.get_next_video_script()
        if video_script_data:
            script_id, script_content, video_id = video_script_data
            print(f"Procesando script de video {script_id} con contenido: {script_content} y video id: {video_id}")
            video_audio_service.process_video_conversion(script_content, script_id, video_id)
        else:
            time.sleep(1)

def frames_worker(redis_service, frames_storage_service):
    print("Iniciando worker de conversión de video a audio...")
    while True:
        # Escucha en la cola "video_scripts_queue"
        frames_script_data = redis_service.get_next_frames_script()
        if frames_script_data:
            script_id, script_content, video_id = frames_script_data
            print(f"Procesando script de frames {script_id} con contenido: {script_content} y video id: {video_id}")
            frames_storage_service.process_video_to_frames(script_content, script_id, video_id)
        else:
            time.sleep(1)

def main():
    # Inicialización de servicios
    redis_service = RedisService()
    script_service = ScriptService(redis_service)
    video_audio_service = VideoAudioService(redis_service)
    frames_storage_service = FramesStorageService(redis_service)
    
    # Crear hilos para cada flujo
    thread_scripts = threading.Thread(target=script_worker, args=(redis_service, script_service))
    thread_video = threading.Thread(target=video_worker, args=(redis_service, video_audio_service))
    thread_frames = threading.Thread(target=frames_worker, args=(redis_service, frames_storage_service))
    
    # Iniciar los hilos
    thread_scripts.start()
    thread_video.start()
    thread_frames.start()
    
    # Espera a que ambos hilos sigan ejecutándose (en este caso, son loops infinitos)
    thread_scripts.join()
    thread_video.join()
    thread_frames.join()

if __name__ == "__main__":
    main()
