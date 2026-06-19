FROM python:3.11-slim

WORKDIR /app

# Copiar requerimientos y código
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el contenido de la raíz
COPY . .

# AJUSTE: Si tu main.py está en /src, debes ejecutarlo desde ahí
# Cambia 'main:app' por 'src.main:app'
CMD alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port 8000