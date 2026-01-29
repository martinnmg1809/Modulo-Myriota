FROM python:3.9-slim

WORKDIR /app

# Copiamos solo lo necesario (NO copiamos .env ni config.py)
COPY requirements.txt .
COPY puente_real.py .

RUN pip install --no-cache-dir -r requirements.txt

# Usamos -u para que los logs de Python salgan directo a la consola de Docker
CMD ["python", "-u", "puente_real.py"]