
# ---- Fase 1: Construir el Entorno ----
# Usamos una imagen oficial de Python como base
FROM python:3.11-slim

# Establecemos el directorio de trabajo dentro del contenedor
WORKDIR /app

# ---- ¡LA PARTE MÁGICA! ----
# Instalamos los paquetes de idioma español ANTES de hacer cualquier otra cosa
# Esto se ejecuta como administrador (root), por lo que sí tenemos permisos
RUN apt-get update && apt-get install -y locales && \
    sed -i -e 's/# es_ES.UTF-8 UTF-8/es_ES.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales

# Configuramos las variables de entorno para que todo el sistema use español
ENV LANG es_ES.UTF-8
ENV LANGUAGE es_ES:es
ENV LC_ALL es_ES.UTF-8

# ---- Fase 2: Preparar la Aplicación ----
# Copiamos primero el archivo de requerimientos
COPY requirements.txt .

# Instalamos las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código de nuestra aplicación
COPY ./app /app/app

# ---- Fase 3: Ejecutar la Aplicación ----
# Exponemos el puerto que Render usará (Render asigna el valor a $PORT)
EXPOSE 10000

# El comando para iniciar la aplicación cuando el contenedor se ponga en marcha
# Uvicorn se enlaza a 0.0.0.0 para ser accesible desde fuera del contenedor
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
