# Grec0AI Backend Worker

Sistema de workers backend escalable para la plataforma Grec0AI, diseñado para procesar videos y ejecutar scripts de Python arbitrarios dentro de contenedores Docker aislados. El sistema gestiona la ejecución de tareas asíncronas, conversión de medios, y persistencia de artefactos generados.

## Tabla de Contenidos

- [Descripción General](#descripción-general)
- [Arquitectura](#arquitectura)
- [Características Principales](#características-principales)
- [Servicios y Componentes](#servicios-y-componentes)
- [Guía de Integración (Colas y Redis)](#guía-de-integración-colas-y-redis)
- [Instalación y Uso](#instalación-y-uso)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Memory Bank](#memory-bank)

## Descripción General

Este proyecto proporciona un sistema de microservicios tipo "worker" que se encarga de:
- **Ejecución de Scripts**: Correr scripts de Python proporcionados por el usuario en entornos Docker aislados (imágenes como `py-graph`, `py-audio`).
- **Procesamiento de Video**: Conversión de video a audio, extracción de frames y metadatos.
- **Ejecución Atómica**: Pasos de ejecución "atómicos" y skills de agentes (código codificado en base64).
- **Despliegue Frontend**: Despliegue efímero de proyectos estáticos HTML o paquetes npm en contenedores.
- **Persistencia**: Guardado de artefactos generados (imágenes, audio, binarios) en MySQL y gestión de estado en Redis.

## Arquitectura

El sistema sigue una arquitectura dirigida por mensajes (Message-driven) utilizando Redis para las colas y Docker para el aislamiento de ejecución.

```mermaid
graph TB
    subgraph "Cliente/API"
        API[API Backend]
    end
    
    subgraph "Sistema de Colas (Redis)"
        Redis[(Redis)]
        SQ[scripts_queue]
        VQ[video_scripts_queue]
        FQ[frames_scripts_queue]
        MQ[metadata_scripts_queue]
        AQ[frontend_queue]
    end
    
    subgraph "Workers (Backend Py Worker)"
        RQW[RQ Worker]
        TW[Traditional Worker (Threaded)]
        
        subgraph "Core Services"
            SS[Script Service]
            AES[Atomic Execution Service]
            VAS[Video Audio Service]
            FSS[Frames Storage Service]
            MSS[Metadata Storage Service]
            FS[Frontend Service]
        end
        
        CS[Container Selector]
    end
    
    subgraph "Runtime Docker"
        PG[py-graph Container]
        PA[py-audio Container]
        PF[python-ffmpeg Container]
        Other[Otros Contenedores]
    end
    
    subgraph "Almacenamiento"
        MySQL[(MySQL Database)]
        ScriptsDir[VOLUME: /scripts]
    end

    API -->|Push Jobs| Redis
    Redis -->|Blpop / RQ| RQW
    Redis -->|Blpop| TW
    
    RQW --> AES
    RQW --> FS
    TW --> SS
    TW --> VAS
    TW --> FSS
    TW --> MSS
    
    AES -->|Select Image| CS
    AES -->|Run| PG
    SS -->|Run| PG
    
    PG -->|Write| ScriptsDir
    PG -->|StdOut| Redis
    
    AES -->|Save Artifacts| MySQL
```

## Características Principales

*   **Soporte Dual de Workers**: Puede funcionar con workers tradicionales (hilos polling `blpop`) o con **RQ (Redis Queue)** para una gestión de trabajos más robusta.
*   **Selección Inteligente de Contenedores**: `ContainerSelector` analiza las importaciones y palabras clave del script para elegir la imagen Docker más adecuada (`matplotlib` -> `py-graph`, `moviepy` -> `py-audio`).
*   **Detección Automática de Archivos**: Los archivos generados por los scripts (imágenes, audio, documentos) son detectados, tipados y guardados automáticamente en MySQL.
*   **Gestión de Dependencias**: Volumen compartido `/scripts` para entrada/salida de archivos temporales entre el host y los contenedores.

## Servicios y Componentes

Los servicios principales se encuentran en `app/services`:

*   **AtomicExecutionService**: Maneja la ejecución de pasos atómicos y "skills". Decodifica código base64, ejecuta en Docker, y gestiona timeouts (300s por defecto, 600s para skills).
*   **ContainerSelector**: Lógica heurística para mapear código a imágenes Docker.
*   **FramesStorageService**: Descarga videos, inyecta scripts de extracción y guarda frames individuales en la base de datos.
*   **MetadataStorageService**: Utiliza `python-ffmpeg` para extraer metadatos técnicos de videos.
*   **FrontendService**: Construye y despliega proyectos frontend (HTML/npm) en contenedores efímeros, exponiendo una URL temporal.
*   **RedisService**: Facade para operaciones de Redis, manejando colas, estados y publicación de resultados.

## Guía de Integración (Colas y Redis)

### Nombres de Colas (Redis Keys)
*   `scripts_queue`: Para ejecución de scripts generales.
*   `video_scripts_queue`: Conversión video -> audio.
*   `frames_scripts_queue`: Extracción de frames.
*   `metadata_scripts_queue`: Extracción de metadatos.
*   `frontend_queue`: Despliegues frontend.

### Formatos de Mensaje
*   General: `"script_id:script_content"`
*   Video/Frames: `"script_id:script_content:video_id"`

### Retorno de Resultados
*   **Estado**: Se actualizan claves como `script_status_<id>` o `step_status_<token>`.
*   **Salida**: Los resultados (stdout, IDs de archivos) se empujan a `results_queue_<id>` o `step_output_<token>`.

## Instalación y Uso

### Prerrequisitos
*   Python 3.x
*   Docker Desktop / Engine instalado y corriendo.
*   Servidor Redis.
*   Servidor MySQL.
*   Imágenes Docker locales necesarias (e.g., `localhost:5000/py-graph`).

### Variables de Entorno
Crea un archivo `.env` o configura las variables:
```bash
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=secret
MYSQL_DB=grec0ai

REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0

# Agent CLI Configuration (opcional)
AGENT_KIND=gemini
AGENT_CLI_CMD=gemini
AGENT_SPEC_ARGS=--spec
AGENT_DOCKER_IMAGE=gemini-cli:latest
AGENT_USE_DOCKER=true
AGENT_WORKDIR=/workspace
AGENT_MAX_RETRIES=2

# Overrides por agente (opcional)
AGENT_GEMINI_CLI_CMD=gemini
AGENT_CLAUDE_CLI_CMD=claude
AGENT_CODEX_CLI_CMD=codex
AGENT_COPILOT_CLI_CMD=copilot
```

### Ejecutar Workers

**Modo Recomendado (RQ):**
```bash
python rq_worker.py
```

2. Añade trabajos a las colas usando el RedisService:
```python
from app.services.redis_service import RedisService

redis_service = RedisService()

# Trabajo de script
redis_service.enqueue_script("script_123", "print('Hello World')")

# Trabajo de conversión de video
redis_service.enqueue_video_conversion("script_456", "script_content", "video_789")

# Trabajo de extracción de frames
redis_service.enqueue_frames_extraction("script_789", "script_content", "video_123")

# Trabajo de extracción de metadatos
redis_service.enqueue_metadata_extraction("script_101", "script_content", "video_456")

# Despliegue de un frontend desde código HTML
html_code = "<h1>Hola</h1>"
redis_service.enqueue_frontend_deployment("deploy_001", html_code)

# Despliegue de un frontend basado en npm (tar.gz codificado en base64)
import base64
with open("my_app.tar.gz", "rb") as f:
    encoded = base64.b64encode(f.read()).decode("utf-8")
redis_service.enqueue_frontend_deployment("deploy_002", encoded, npm=True)

# Trabajo de agentes CLI (requiere main.py en ejecución)
redis_service.enqueue_agent_task(
    "issue_123",
    "gemini",
    "/ruta/al/proyecto",
    "# spec.md content"
)

# Obtener la URL generada para cualquiera de los despliegues
url = redis_service.r.blpop("results_queue_deploy_002")[1].decode("utf-8")
print(url)
```

#### Modo Tradicional

```bash
python main.py
```

### Nombres de Colas Redis

- `scripts_queue`: Scripts para generación de imágenes
- `video_scripts_queue`: Scripts para conversión video-audio
- `frames_scripts_queue`: Scripts para extracción de frames
- `metadata_scripts_queue`: Scripts para extracción de metadatos
- `frontend_queue`: Despliegue de frontends (HTML o proyectos npm)
- `agents_queue`: Tareas para agentes CLI
- `agent_results_queue`: Resultados de agentes CLI

## Especificaciones Técnicas

### Dependencias

```
fastapi==0.104.1
uvicorn==0.24.0
mysql-connector-python==8.2.0
redis==5.0.1
python-dotenv==1.0.0
rq==1.15.1
```

### Formato de Datos

#### Scripts Queue
```
"script_id:script_content"
```

#### Video/Frames/Metadata Queues
```
"script_id:script_content:video_id"
```

#### Agents Queue
```json
{
  "task_issue_id": "issue_123",
  "agent_kind": "gemini",
  "project_path": "/ruta/al/proyecto",
  "spec_md_content": "# spec.md",
  "params": {
    "action": "implement"
  }
}
```

#### Estados de Procesamiento
- `in_progress`: Trabajo en curso
- `completed`: Trabajo completado exitosamente
- `failed`: Trabajo falló con error

### Placeholders en Scripts

Los scripts pueden contener placeholders que se reemplazan dinámicamente:

- `{{input_name}}`: Nombre del archivo de entrada (sin extensión)

### Estructura de Directorios

```
Grec0AI_backend_py_worker/
├── app/
│   ├── services/          # Lógica de negocio y servicios
│   │   ├── atomic_execution_service.py
│   │   ├── container_selector.py
│   │   ├── redis_service.py
│   │   └── ...
│   └── utils/             # Utilidades (Database, etc.)
├── scripts/               # Directorio de trabajo temporal (montado en Docker)
├── main.py                # Entrypoint worker tradicional
├── rq_worker.py           # Entrypoint worker RQ
├── requirements.txt       # Dependencias Python
└── README.md              # Documentación
```

## Memory Bank

Este proyecto utiliza **Memory Bank MCP** para mantener la documentación y el contexto sincronizados con el código.

*   **RAG System**: El código está indexado para búsquedas semánticas.
*   **Documentación Viva**: La documentación en `.memorybank/` se genera y actualiza automáticamente basada en el código.
*   **Reglas**:
    1.  Siempre consultar el Memory Bank antes de implementar cambios (`memorybank_search`).
    2.  Reindexar inmediatamente después de cualquier modificación (`memorybank_index_code`).
