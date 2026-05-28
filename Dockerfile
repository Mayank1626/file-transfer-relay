FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and app directories
COPY run.py .
COPY app/ ./app/

EXPOSE 5000

# Run using Gunicorn targeting the run:app entrypoint
CMD ["gunicorn", "run:app", "--workers", "2", "--threads", "4", "--timeout", "120", "--access-logfile", "-", "-b", "0.0.0.0:5000"]
