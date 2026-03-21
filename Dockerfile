FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install boto3 gunicorn  # Ensure production-ready packages exist

# Copy app files
# Note: When deploying, rename app_minio.py into app.py
COPY app_minio.py ./app.py
COPY templates/ ./templates/

EXPOSE 5000

# Run using Gunicorn with generous stream timeout
CMD ["gunicorn", "app:app", "--timeout", "300", "-b", "0.0.0.0:5000"]
