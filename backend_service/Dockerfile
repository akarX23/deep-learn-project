FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend_service /app/backend_service
COPY project /app/project
COPY uploads /app/uploads

EXPOSE 8001

CMD ["python", "-m", "backend_service.app.main"]
