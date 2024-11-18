FROM python:3.11-slim

# Instala las dependencias del sistema y Calibre
RUN apt-get update && apt-get install -y \
    calibre \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Instala las dependencias de Python
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt

# Expone el puerto para FastAPI
EXPOSE 8000

# Comando para ejecutar la aplicación
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
