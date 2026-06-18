FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY ui_frontend /app/ui_frontend
COPY project /app/project

EXPOSE 8501

CMD ["python", "-m", "streamlit", "run", "ui_frontend/app.py", "--server.headless=true", "--server.port=8501", "--server.address=0.0.0.0"]