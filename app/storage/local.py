import os
from flask import request
from werkzeug.utils import secure_filename
from app.storage.base import StorageEngine

class LocalStorageEngine(StorageEngine):
    """Storage Engine using the local filesystem."""
    
    def __init__(self):
        self.upload_folder = None
        
    def init_app(self, app):
        self.upload_folder = app.config['UPLOAD_FOLDER']
        os.makedirs(self.upload_folder, exist_ok=True)
        
    def _get_filepath(self, pin, filename):
        safe_name = secure_filename(filename) or "shared_file"
        return os.path.join(self.upload_folder, f"{pin}_{safe_name}")
        
    def generate_upload_url(self, pin, filename, content_type):
        # Return local fallback endpoint as the upload URL
        host_url = request.host_url.rstrip('/')
        return f"{host_url}/upload/{pin}"
        
    def generate_download_url(self, pin, filename):
        host_url = request.host_url.rstrip('/')
        return f"{host_url}/download/{pin}"
        
    def upload_file(self, pin, file):
        filename = file.filename
        filepath = self._get_filepath(pin, filename)
        file.save(filepath)
        return filepath
        
    def download_file(self, pin, filename):
        filepath = self._get_filepath(pin, filename)
        if os.path.exists(filepath):
            return filepath, True
        return None, False
        
    def delete_file(self, pin, filename):
        filepath = self._get_filepath(pin, filename)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception:
                pass
                
    def exists(self, pin, filename):
        filepath = self._get_filepath(pin, filename)
        return os.path.exists(filepath)

