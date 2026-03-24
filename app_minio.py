import os
import random
import time
import json
from flask import Flask, request, jsonify
import boto3
import redis
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

app = Flask(__name__)

@app.route('/')
def index():
    try:
        # Direct static read to bypass Jinja path deadlocks on VPS
        with open('templates/index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error loading template: {str(e)}", 500

# Minio / S3 Configuration (Populated via Docker environment variables)
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "http://localhost:9000")
S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "admin")
S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY", "supersecret")
S3_BUCKET = os.environ.get("S3_BUCKET", "filedrop")

# Connect to Minio S3 API
s3_client = boto3.client(
    's3',
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    config=boto3.session.Config(signature_version='s3v4') # Required for MinIO
)
# --- ENSURE BUCKET EXISTS ---
try:
    s3_client.create_bucket(Bucket=S3_BUCKET)
    print(f"Bucket '{S3_BUCKET}' ensured.")
except Exception:
    pass # Bucket already exists or owned by you

# --- REDIS SETUP (Scaling & Session Storage) ---
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# --- RATE LIMITER SETUP ---
limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri=f"redis://{REDIS_HOST}:{REDIS_PORT}",
    strategy="fixed-window"
)

def load_session(pin):
    try:
        data = redis_client.get(f"sess:{pin}")
        return json.loads(data) if data else None
    except Exception:
        return None

def save_session(pin, data):
    try:
        # Auto-expire after 1 hour (3600 seconds)
        redis_client.setex(f"sess:{pin}", 3600, json.dumps(data))
    except Exception:
        pass

def generate_pin():
    while True:
        pin = str(random.randint(100000, 999999))
        if not redis_client.exists(f"sess:{pin}"):
            return pin

@app.route('/request-pin', methods=['GET'])
@limiter.limit("10 per minute")
def request_pin():
    pin = generate_pin()
    data = {
        'filename': None,
        'timestamp': time.time(),
        'status': 'waiting_for_link'
    }
    save_session(pin, data)
    return jsonify({'pin': pin})

@app.route('/upload-link/<pin>', methods=['POST'])
def get_upload_link(pin):
    data = load_session(pin)
    if not data:
        return jsonify({'error': 'Invalid or expired PIN.'}), 404
        
    req_data = request.get_json() or {}
    filename = req_data.get('filename', 'shared_file')
    content_type = req_data.get('content_type', 'application/octet-stream')
    
    # Generate Presigned URL for PUT Upload
    key = f"{pin}_{filename}"
    try:
        req_host = request.host.split(':')[0]
        protocol = request.headers.get('X-Forwarded-Proto', 'http')
        
        signing_client = boto3.client(
            's3',
            endpoint_url=f"{protocol}://{req_host}" if protocol == 'https' else f"http://{req_host}:9000",
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
            config=boto3.session.Config(
                signature_version='s3v4',
                s3={'addressing_style': 'path'}
            )
        )
        url = signing_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': S3_BUCKET, 
                'Key': key,
                'ContentType': content_type # 🟢 Force signature to match browser Content-Type!
            },
            ExpiresIn=900
        )
        
        # Update session dictionary
        data['filename'] = filename
        # On Minio Architecture, it becomes ready as soon as client starts pipe.
        data['status'] = 'ready_for_download' 
        data['timestamp'] = time.time()
        save_session(pin, data)
        
        return jsonify({
            'upload_url': url,
            'key': key
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload/<pin>', methods=['POST'])
def upload_file(pin):
    """Fallback upload handler that streams bytes via Flask to bypass browser CORS block."""
    data = load_session(pin)
    if not data:
        return jsonify({'error': 'Invalid or expired PIN.'}), 404
        
    if 'file' not in request.files:
        return jsonify({'error': 'No file element in request'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    filename = file.filename
    key = f"{pin}_{filename}"
    
    try:
        # Use global s3_client to retain signature_version='s3v4' config
        s3_client.upload_fileobj(file.stream, S3_BUCKET, key)
        
        # Update session state to match structure
        data['filename'] = filename
        data['status'] = 'ready_for_download'
        data['timestamp'] = time.time()
        save_session(pin, data)
        
        return jsonify({'success': True, 'key': key})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/check/<pin>', methods=['GET'])
@limiter.limit("20 per minute")
def check_session(pin):
    data = load_session(pin)
    if not data:
        return jsonify({'error': 'Invalid PIN.'}), 404
    return jsonify({
        'status': 'ready' if data['status'] == 'ready_for_download' else 'waiting',
        'filename': data.get('filename')
    })

@app.route('/download-link/<pin>', methods=['GET'])
@limiter.limit("5 per minute")
def get_download_link(pin):
    data = load_session(pin)
    if not data:
        return jsonify({'error': 'Invalid PIN.'}), 404
        
    filename = data.get('filename')
    key = f"{pin}_{filename}"
    try:
        req_host = request.host.split(':')[0]
        protocol = request.headers.get('X-Forwarded-Proto', 'http')
        
        signing_client = boto3.client(
            's3',
            endpoint_url=f"{protocol}://{req_host}" if protocol == 'https' else f"http://{req_host}:9000",
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
            config=boto3.session.Config(
                signature_version='s3v4',
                s3={'addressing_style': 'path'} # 🟢 Force Path address for Nginx subfolder relay!
            )
        )
        url = signing_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': S3_BUCKET, 
                'Key': key,
                'ResponseContentDisposition': f'attachment; filename="{filename}"'
            },
            ExpiresIn=3600  # 1 hour
        )
        return jsonify({'download_url': url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Enable Max Content Length for large uploads 1GB+
    app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024 
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, threaded=True)
