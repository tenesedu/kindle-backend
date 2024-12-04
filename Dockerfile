# Usa una imagen base de Python
FROM python:3.11-slim

# Establece el directorio de trabajo en el contenedor
WORKDIR /app

# Copia los archivos del proyecto al contenedor
COPY . /app

# Instala las dependencias del sistema necesarias
RUN apt-get update && apt-get install -y \
    calibre \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copia el archivo de dependencias e instálalas
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expone el puerto para FastAPI
EXPOSE 8000

# Comando para ejecutar la aplicación
CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]
