import os
import random
import time
import threading
from flask import Flask, request, jsonify, send_file, render_template, after_this_request
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Temporary storage configuration
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max

# In-memory dictionary to track PINs and their associated files
sessions = {}

# Cleanup routine to delete files older than 1 hour
def cleanup_old_sessions():
    while True:
        time.sleep(600)
        current_time = time.time()
        expired_pins = []
        for pin, data in list(sessions.items()):
            if current_time - data['timestamp'] > 3600:
                expired_pins.append(pin)
                try:
                    if data.get('filepath') and os.path.exists(data['filepath']):
                        os.remove(data['filepath'])
                except Exception as e:
                    print(f"Cleanup error for {pin}: {e}")
        for pin in expired_pins:
            sessions.pop(pin, None)

threading.Thread(target=cleanup_old_sessions, daemon=True).start()

def generate_pin():
    while True:
        pin = str(random.randint(100000, 999999))
        if pin not in sessions:
            return pin

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/request-pin', methods=['GET'])
def request_pin():
    pin = generate_pin()
    sessions[pin] = {
        'filename': None,
        'filepath': None,
        'timestamp': time.time(),
        'status': 'waiting_for_upload'
    }
    return jsonify({'pin': pin})

@app.route('/upload/<pin>', methods=['POST'])
def upload_file(pin):
    if pin not in sessions:
        return jsonify({'error': 'Invalid or expired PIN.'}), 404
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    filename = secure_filename(file.filename)
    if not filename:
        filename = "shared_file"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{pin}_{filename}")
    file.save(filepath)
    sessions[pin]['filename'] = filename
    sessions[pin]['filepath'] = filepath
    sessions[pin]['status'] = 'ready_for_download'
    sessions[pin]['timestamp'] = time.time()
    return jsonify({'message': 'File uploaded successfully', 'pin': pin})

@app.route('/check/<pin>', methods=['GET'])
def check_session(pin):
    if pin not in sessions:
        return jsonify({'error': 'Invalid PIN.'}), 404
    data = sessions[pin]
    if data['status'] == 'ready_for_download':
        return jsonify({'status': 'ready', 'filename': data['filename']})
    else:
        return jsonify({'status': 'waiting'})

@app.route('/download/<pin>', methods=['GET'])
def download_file(pin):
    if pin not in sessions:
        return jsonify({'error': 'Invalid PIN.'}), 404
    data = sessions[pin]
    if data['status'] != 'ready_for_download' or not data['filepath']:
        return jsonify({'error': 'File not ready yet.'}), 400
    filepath = data['filepath']
    filename = data['filename']
    try:
        response = send_file(filepath, as_attachment=True, download_name=filename)

        @after_this_request
        def cleanup(resp):
            # Clean up file and session AFTER streaming is done
            sessions.pop(pin, None)
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception:
                pass
            return resp

        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
