FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py whatsapp.py risk.py ./

EXPOSE 8000

# Render (e outros PaaS) injetam a variável PORT dinamicamente; localmente
# cai no padrão 8000 se PORT não estiver definida.
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"]
