# Usar una imagen base de Python
FROM python:3.9-slim

# Establecer directorio de trabajo
WORKDIR /app

# Copiar los archivos del worker
COPY . /app

# Instalar las dependencias necesarias
RUN pip install redis

# Exponer el puerto si es necesario (en caso de monitorización externa)
EXPOSE 5000

# Comando por defecto para ejecutar el worker Python
CMD ["python", "redis_worker.py"]
