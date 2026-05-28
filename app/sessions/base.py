from abc import ABC, abstractmethod

class SessionProvider(ABC):
    """Abstract Base Class for Session Providers."""
    
    @abstractmethod
    def init_app(self, app):
        """Initializes the session provider with Flask configuration."""
        pass
        
    @abstractmethod
    def get_session(self, pin):
        """Retrieves session data associated with the 6-digit PIN.
        
        Args:
            pin (str): The unique 6-digit session PIN.
            
        Returns:
            dict: Session data or None if not found/expired.
        """
        pass
        
    @abstractmethod
    def save_session(self, pin, data, expire_seconds=3600):
        """Saves session data associated with the 6-digit PIN.
        
        Args:
            pin (str): The unique 6-digit session PIN.
            data (dict): Session dictionary data payload.
            expire_seconds (int): Auto-expiration time in seconds.
        """
        pass
        
    @abstractmethod
    def exists(self, pin):
        """Checks if a session matching the 6-digit PIN exists.
        
        Args:
            pin (str): The unique 6-digit session PIN.
            
        Returns:
            bool: True if exists, False otherwise.
        """
        pass
        
    @abstractmethod
    def delete_session(self, pin):
        """Deletes/invalidates the session matching the 6-digit PIN.
        
        Args:
            pin (str): The unique 6-digit session PIN.
        """
        pass
