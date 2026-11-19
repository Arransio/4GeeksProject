# Imagen oficial de Python + uv
# Build con contexto = services/ (asi se aplica services/.dockerignore):
#   docker build -f services/Dockerfile -t healthcore-incident-manager:latest services/
#   docker compose up --build   (ver docker-compose.yml en la raiz)
# Ejecutar:
#   docker run --rm -p 8000:8000 healthcore-incident-manager:latest
#
# uv instala las dependencias desde requirements.txt con:
#   uv pip install -r requeriments.txt
# El servidor Uvicorn arranca con --reload habilitado (desarrollo).

FROM python:3.11-slim

# 1) Instalar uv (gestor de paquetes rapido)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# 2) Instalar las dependencias desde requeriments.txt con uv pip
#    (la fuente unica en el repo es incident_manager/requirements.txt; se copia
#     como requeriments.txt para respetar el nombre del comando de la consigna)
#    Se copia solo el manifiesto para mantener cacheada la capa.
COPY incident_manager/requirements.txt ./requeriments.txt
RUN uv pip install --system -r requeriments.txt

# 3) Codigo del servicio conservando el paquete services.incident_manager
#    (el codigo importa `services.incident_manager.*`, igual que en el repo)
COPY . ./services/
# asgi.py (modulo con el objeto `app`) tambien en la raiz de /app para uvicorn
COPY asgi.py ./asgi.py

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app
EXPOSE 8000

# 4) Uvicorn con --reload habilitado (asgi.py expone el objeto `app`)
CMD ["uvicorn", "--host", "0.0.0.0", "--port", "8000", "--reload", "asgi:app"]