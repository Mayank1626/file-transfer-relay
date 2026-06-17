import time
from flask import request, jsonify, current_app, send_file
from app.api import api_bp
from app.sessions import get_sessions
from app.storage import get_storage
from app.utils.state_machine import TransferState, TransferStateMachine
from app.utils.helpers import sanitize_filename
from app.middleware.security import get_limiter

# Retrieve limiter instance
limiter = get_limiter()

def get_limiter_decorator(limit_string):
    if limiter:
        return limiter.limit(limit_string)
    return lambda x: x

@api_bp.route('/upload-link/<pin>', methods=['POST'])
@get_limiter_decorator("20 per hour")
def get_upload_link(pin):
    """Generates a presigned direct upload URL (MinIO/S3 mode)."""
    sessions = get_sessions()
    session_data = sessions.get_session(pin)
    
    if not session_data:
        current_app.logger.warning(f"Upload link request: Invalid PIN {pin}")
        return jsonify({'error': 'Invalid or expired PIN.'}), 404
        
    # Enforce state machine transition
    try:
        session_data = TransferStateMachine.transition(session_data, TransferState.UPLOADING)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
        
    req_data = request.get_json() or {}
    raw_filename = req_data.get('filename', 'shared_file')
    filename = sanitize_filename(raw_filename)
    content_type = req_data.get('content_type', 'application/octet-stream')
    
    storage = get_storage()
    try:
        # Generate upload presigned S3 URL or local endpoint
        upload_url = storage.generate_upload_url(pin, filename, content_type)
        key = f"{pin}_{filename}"
        
        # Save filename inside session dictionary
        session_data['filename'] = filename
        session_data['filepath'] = storage._get_filepath(pin, filename) if hasattr(storage, '_get_filepath') else None
        
        sessions.save_session(pin, session_data)
        current_app.logger.info(f"Generated upload URL for {filename} (PIN: {pin})")
        
        return jsonify({
            'upload_url': upload_url,
            'key': key
        })
    except Exception as e:
        current_app.logger.error(f"Upload link generation failed: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/upload/<pin>', methods=['POST', 'PUT'])
def upload_file(pin):
    """Fallback handler that streams raw bytes directly via Flask."""
    sessions = get_sessions()
    session_data = sessions.get_session(pin)
    
    if not session_data:
        return jsonify({'error': 'Invalid or expired PIN.'}), 404
        
    storage = get_storage()
    is_multipart = 'file' in request.files
    
    if is_multipart:
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        filename = sanitize_filename(file.filename)
    else:
        # Raw bytes PUT upload
        filename = session_data.get('filename')
        if not filename:
            filename = 'shared_file'
    
    try:
        # Enforce state transitions
        if session_data.get('status') != TransferState.UPLOADING:
            session_data = TransferStateMachine.transition(session_data, TransferState.UPLOADING)
            
        session_data = TransferStateMachine.transition(session_data, TransferState.UPLOADED)
        sessions.save_session(pin, session_data)
        
        # Save file to storage backend (MinIO / Local disk)
        if is_multipart:
            filepath_or_key = storage.upload_file(pin, file)
        else:
            if hasattr(storage, '_get_filepath'):
                filepath = storage._get_filepath(pin, filename)
                with open(filepath, 'wb') as f:
                    chunk_size = 8192
                    while True:
                        chunk = request.stream.read(chunk_size)
                        if len(chunk) == 0:
                            break
                        f.write(chunk)
                filepath_or_key = filepath
            else:
                # S3 Storage Stream
                class StreamFile:
                    def __init__(self, stream, name):
                        self.stream = stream
                        self.filename = name
                filepath_or_key = storage.upload_file(pin, StreamFile(request.stream, filename))
        
        # Verification stage: Perform length checks and confirm writes
        session_data = TransferStateMachine.transition(session_data, TransferState.VERIFIED)
        
        # Update session to ready status
        session_data['filename'] = filename
        if not session_data.get('filepath'):
            session_data['filepath'] = filepath_or_key
            
        session_data = TransferStateMachine.transition(session_data, TransferState.READY)
        sessions.save_session(pin, session_data)
        
        current_app.logger.info(f"Stream verification passed. File available for download (PIN: {pin})")
        return jsonify({'success': True, 'key': filepath_or_key})
        
    except Exception as e:
        current_app.logger.error(f"Fallback upload failed: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/upload/verify/<pin>', methods=['POST'])
def verify_upload(pin):
    """Verifies that an S3/MinIO upload completed successfully and makes it download-ready."""
    sessions = get_sessions()
    session_data = sessions.get_session(pin)
    
    if not session_data:
        return jsonify({'error': 'Invalid PIN.'}), 404
        
    try:
        # Move state UPLOADING -> UPLOADED -> VERIFIED -> READY
        if session_data['status'] == TransferState.UPLOADING:
            session_data = TransferStateMachine.transition(session_data, TransferState.UPLOADED)
            
        session_data = TransferStateMachine.transition(session_data, TransferState.VERIFIED)
        session_data = TransferStateMachine.transition(session_data, TransferState.READY)
        sessions.save_session(pin, session_data)
        
        current_app.logger.info(f"Direct stream verification passed. File available for download (PIN: {pin})")
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

def _attempt_self_healing(session_data, pin):
    """Helper to transition session status to READY if the file is found in storage.
    This provides robust self-healing and backward-compatibility with older Android clients.
    """
    status = session_data.get('status')
    if status == TransferState.READY:
        return True, session_data

    filename = session_data.get('filename')
    if filename and status in (TransferState.CREATED, TransferState.UPLOADING, TransferState.UPLOADED, TransferState.VERIFIED):
        storage = get_storage()
        try:
            if storage.exists(pin, filename):
                if status == TransferState.CREATED:
                    session_data = TransferStateMachine.transition(session_data, TransferState.UPLOADING)
                if session_data['status'] == TransferState.UPLOADING:
                    session_data = TransferStateMachine.transition(session_data, TransferState.UPLOADED)
                if session_data['status'] == TransferState.UPLOADED:
                    session_data = TransferStateMachine.transition(session_data, TransferState.VERIFIED)
                if session_data['status'] == TransferState.VERIFIED:
                    session_data = TransferStateMachine.transition(session_data, TransferState.READY)
                
                sessions = get_sessions()
                sessions.save_session(pin, session_data)
                current_app.logger.info(f"Self-healing: Auto-recovered session {pin} to READY status.")
                return True, session_data
        except Exception as e:
            current_app.logger.warning(f"Self-healing check failed for session {pin}: {e}")
            
    return False, session_data

@api_bp.route('/check/<pin>', methods=['GET'])
@get_limiter_decorator("5 per minute")
def check_session(pin):
    """Queries pairing status to check if a file is ready to download."""
    sessions = get_sessions()
    session_data = sessions.get_session(pin)
    
    if not session_data:
        return jsonify({'error': 'Invalid PIN.'}), 404
        
    # Attempt self-healing if the state is not READY yet
    recovered, session_data = _attempt_self_healing(session_data, pin)
    
    status = session_data.get('status')
    if status == TransferState.READY:
        return jsonify({
            'status': 'ready',
            'filename': session_data.get('filename')
        })
    return jsonify({
        'status': 'waiting'
    })

@api_bp.route('/download-link/<pin>', methods=['GET'])
@get_limiter_decorator("5 per minute")
def get_download_link(pin):
    """Retrieves a secure download link for S3 or Local storage."""
    sessions = get_sessions()
    session_data = sessions.get_session(pin)
    
    if not session_data:
        return jsonify({'error': 'Invalid PIN.'}), 404
        
    # Attempt self-healing if not READY
    recovered, session_data = _attempt_self_healing(session_data, pin)
    
    if session_data.get('status') != TransferState.READY:
        return jsonify({'error': 'File not ready yet.'}), 400
        
    filename = session_data.get('filename')
    storage = get_storage()
    
    try:
        download_url = storage.generate_download_url(pin, filename)
        return jsonify({'download_url': download_url})
    except Exception as e:
        current_app.logger.error(f"Download authorization failed: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/download/<pin>', methods=['GET'])
def download_file(pin):
    """Direct route for downloading files locally (local storage mode endpoint)."""
    sessions = get_sessions()
    session_data = sessions.get_session(pin)
    
    if not session_data:
        return jsonify({'error': 'Invalid PIN.'}), 404
        
    # Attempt self-healing if not READY
    recovered, session_data = _attempt_self_healing(session_data, pin)
    
    if session_data.get('status') != TransferState.READY:
        return jsonify({'error': 'File not ready yet.'}), 400
        
    filename = session_data.get('filename')
    storage = get_storage()
    
    try:
        file_payload, as_attachment = storage.download_file(pin, filename)
        if not file_payload:
            return jsonify({'error': 'File not found.'}), 404
            
        # Return local file binary attachment stream
        return send_file(
            file_payload,
            as_attachment=as_attachment,
            download_name=filename
        )
    except Exception as e:
        current_app.logger.error(f"Direct stream download failure: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/download-complete/<pin>', methods=['POST'])
def download_complete(pin):
    """Triggers immediate server-side deletion of file and session details once downloaded."""
    sessions = get_sessions()
    session_data = sessions.get_session(pin)
    
    if not session_data:
        return jsonify({'success': True})  # Already wiped
        
    filename = session_data.get('filename')
    storage = get_storage()
    
    try:
        # Set state to DOWNLOADED
        session_data = TransferStateMachine.transition(session_data, TransferState.DOWNLOADED)
        
        # Permanently purge file payload
        storage.delete_file(pin, filename)
        
        # Permanently purge session dictionary
        sessions.delete_session(pin)
        
        current_app.logger.info(f"Instant Wipe Protocol: Purged file and session data for PIN: {pin}")
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f"Instant Wipe Protocol failed for PIN {pin}: {e}")
        return jsonify({'error': str(e)}), 500
