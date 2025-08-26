   ```bash
    #!/usr/bin/env bash
    # exit on error
    set -o errexit

    # 1. Instala las dependencias de Python
    pip install -r requirements.txt

    # 2. Instala las dependencias del sistema operativo (locales en español)
    apt-get update
    apt-get install -y locales

    # 3. Configura el idioma español
    # Descomenta la línea del idioma español en el archivo de configuración
    sed -i -e 's/# es_ES.UTF-8 UTF-8/es_ES.UTF-8 UTF-8/' /etc/locale.gen
    # Regenera los archivos de localización
    dpkg-reconfigure --frontend=noninteractive locales
    # Establece el idioma por defecto
    update-locale LANG=es_ES.UTF-8
    ```