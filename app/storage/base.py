from abc import ABC, abstractmethod

class StorageEngine(ABC):
    """Abstract Base Class for Storage Engines."""
    
    @abstractmethod
    def init_app(self, app):
        """Initializes the storage engine with Flask configuration."""
        pass
        
    @abstractmethod
    def generate_upload_url(self, pin, filename, content_type):
        """Generates a URL endpoint where the client can upload/stream the file.
        
        Args:
            pin (str): The unique 6-digit session PIN.
            filename (str): The name of the file.
            content_type (str): The MIME type of the file.
            
        Returns:
            str: Upload URL.
        """
        pass
        
    @abstractmethod
    def generate_download_url(self, pin, filename):
        """Generates a URL endpoint where the client can download the file.
        
        Args:
            pin (str): The unique 6-digit session PIN.
            filename (str): The name of the file.
            
        Returns:
            str: Download URL.
        """
        pass
        
    @abstractmethod
    def upload_file(self, pin, file):
        """Fallback method to stream and write the file directly through Flask.
        
        Args:
            pin (str): The unique 6-digit session PIN.
            file (FileStorage): The Flask file storage request stream object.
            
        Returns:
            str: Unique key or path representing the uploaded file.
        """
        pass
        
    @abstractmethod
    def download_file(self, pin, filename):
        """Downloads/retrieves the raw file payload from storage.
        
        Args:
            pin (str): The unique 6-digit session PIN.
            filename (str): The name of the file.
            
        Returns:
            tuple: (file_stream_or_path, as_attachment_flag)
        """
        pass
        
    @abstractmethod
    def delete_file(self, pin, filename):
        """Permanently deletes the file payload from storage.
        
        Args:
            pin (str): The unique 6-digit session PIN.
            filename (str): The name of the file.
        """
        pass
