FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install boto3 gunicorn  # Ensure production-ready packages exist

# Copy app files
COPY app_minio.py .
COPY templates/ ./templates/
COPY static/ ./static/

EXPOSE 5000

# Run using Gunicorn with generous stream timeout and multithreading
CMD ["gunicorn", "app_minio:app", "--workers", "2", "--threads", "4", "--timeout", "120", "--access-logfile", "-", "-b", "0.0.0.0:5000"]
