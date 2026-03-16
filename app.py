import os
import random
import time
import threading
import zipfile
import json
from flask import Flask, request, jsonify, send_file, render_template

app = Flask(__name__)

# Temporary storage configuration
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max

# --- STATELESS SESSIONS (Disk backed for Multi-worker support) ---
def get_session_path(pin):
    return os.path.join(app.config['UPLOAD_FOLDER'], f"sess_{pin}.json")

def load_session(pin):
    path = get_session_path(pin)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def save_session(pin, data):
    path = get_session_path(pin)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)

# Cleanup routine to delete files older than 1 hour
def cleanup_old_sessions():
    while True:
        time.sleep(600)  # 10 minutes
        current_time = time.time()
        try:
            for filename in os.listdir(app.config['UPLOAD_FOLDER']):
                if filename.startswith("sess_") and filename.endswith(".json"):
                    pin = filename[5:-5]
                    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        if current_time - data.get('timestamp', 0) > 3600:
                            # Delete file payload if exists
                            if data.get('filepath') and os.path.exists(data['filepath']):
                                if os.path.exists(data['filepath']):
                                    os.remove(data['filepath'])
                            # Delete session file
                            os.remove(path)
                    except Exception as e:
                        print(f"Cleanup error for {pin}: {e}")
        except Exception as ex:
            print(f"Directory listing error in cleanup: {ex}")

threading.Thread(target=cleanup_old_sessions, daemon=True).start()

def generate_pin():
    while True:
        pin = str(random.randint(100000, 999999))
        if not os.path.exists(get_session_path(pin)):
            return pin

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/request-pin', methods=['GET'])
def request_pin():
    pin = generate_pin()
    data = {
        'filename': None,
        'filepath': None,
        'timestamp': time.time(),
        'status': 'waiting_for_upload'
    }
    save_session(pin, data)
    return jsonify({'pin': pin})

@app.route('/upload/<pin>', methods=['POST'])
def upload_file(pin):
    data = load_session(pin)
    if not data:
        return jsonify({'error': 'Invalid or expired PIN.'}), 404
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    files = request.files.getlist('file')
    files = [f for f in files if f.filename != '']
    
    if not files:
        return jsonify({'error': 'Empty filename'}), 400
    
    from werkzeug.utils import secure_filename
    if len(files) == 1:
        # Single file — save directly
        file = files[0]
        filename = secure_filename(file.filename) or "shared_file"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{pin}_{filename}")
        file.save(filepath)
    else:
        # Multiple files — ZIP them server-side
        filename = f"FileDrop_{len(files)}_files.zip"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{pin}_{filename}")
        with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
            for f in files:
                safe_name = secure_filename(f.filename) or "file"
                temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{pin}_temp_{safe_name}")
                f.save(temp_path)
                zf.write(temp_path, safe_name)
                os.remove(temp_path)
    
    data['filename'] = filename
    data['filepath'] = filepath
    data['status'] = 'ready_for_download'
    data['timestamp'] = time.time()
    save_session(pin, data)
    return jsonify({'message': 'File uploaded successfully', 'pin': pin})

@app.route('/check/<pin>', methods=['GET'])
def check_session(pin):
    data = load_session(pin)
    if not data:
        return jsonify({'error': 'Invalid PIN.'}), 404
    if data['status'] == 'ready_for_download':
        return jsonify({'status': 'ready', 'filename': data['filename']})
    else:
        return jsonify({'status': 'waiting'})

@app.route('/download/<pin>', methods=['GET'])
def download_file(pin):
    data = load_session(pin)
    if not data:
        return jsonify({'error': 'Invalid PIN.'}), 404
    if data['status'] != 'ready_for_download' or not data['filepath']:
        return jsonify({'error': 'File not ready yet.'}), 400
    filepath = data['filepath']
    filename = data['filename']
    try:
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
