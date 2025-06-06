# Grec0AI Backend Worker

Este proyecto contiene varios servicios que ejecutan scripts de procesamiento de videos, extracción de frames y metadatos utilizando contenedores Docker. Anteriormente los workers se implementaban con un bucle que leía colas de Redis manualmente. Ahora se ofrece una alternativa basada en **RQ** (Redis Queue) para gestionar las tareas de forma más robusta y en tiempo real.

## Requisitos

Instala las dependencias con:

```bash
pip install -r requirements.txt
```

## Uso

1. Añade trabajos a las colas correspondientes de RQ. Los nombres de las colas son:
   - `scripts_queue`
   - `video_scripts_queue`
   - `frames_scripts_queue`
   - `metadata_scripts_queue`

2. Inicia el worker de RQ ejecutando:

```bash
python rq_worker.py
```

Los trabajos utilizan las funciones definidas en `app/services/rq_tasks.py`, las cuales hacen uso de los servicios existentes. De esta manera el flujo de procesamiento se mantiene, pero con las ventajas de una cola de trabajos real.
