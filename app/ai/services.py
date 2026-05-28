from abc import ABC, abstractmethod

class AIMemoryService(ABC):
    """Abstract interface defining the future AI Memory OS execution capabilities."""
    
    @abstractmethod
    def extract_text_from_payload(self, file_path_or_stream, mime_type):
        """Runs Tesseract OCR or deep document extraction on uploaded files."""
        pass
        
    @abstractmethod
    def generate_embeddings(self, text_content):
        """Generates vector embeddings (e.g. via sentence-transformers or external model)."""
        pass
        
    @abstractmethod
    def index_vector(self, embedding, metadata):
        """Writes the generated high-dimensional embedding into the Vector Database."""
        pass
        
    @abstractmethod
    def search_semantic_memory(self, query_string, top_k=5):
        """Performs cosine-similarity vector queries against user interaction history."""
        pass

class AICrossDeviceController(ABC):
    """Abstract interface governing workspace automation and clipboard syncing."""
    
    @abstractmethod
    def sync_clipboard(self, device_id, raw_data):
        """Automates silent peer clipboard replication."""
        pass
        
    @abstractmethod
    def execute_command(self, workspace_cmd_string):
        """Triggers local desktop automated tasks (run build, format layout, search web)."""
        pass

# Simple Mock Services for current Phase 9 Scaffold
class MockAIMemoryService(AIMemoryService):
    def extract_text_from_payload(self, file_path_or_stream, mime_type):
        return "Scaffold: OCR text content extractions."
        
    def generate_embeddings(self, text_content):
        return [0.0] * 384  # Standard vector dimensions placeholder
        
    def index_vector(self, embedding, metadata):
        return True
        
    def search_semantic_memory(self, query_string, top_k=5):
        return []

class MockAICrossDeviceController(AICrossDeviceController):
    def sync_clipboard(self, device_id, raw_data):
        return True
        
    def execute_command(self, workspace_cmd_string):
        return "Scaffold: Automated workspace task execution mock."
