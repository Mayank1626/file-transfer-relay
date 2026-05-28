import time

class TransferState:
    """Allowed states in the file transfer lifecycle."""
    CREATED = "CREATED"
    UPLOADING = "UPLOADING"
    UPLOADED = "UPLOADED"
    VERIFIED = "VERIFIED"
    READY = "READY"
    DOWNLOADED = "DOWNLOADED"
    EXPIRED = "EXPIRED"

class TransferStateMachine:
    """Enforces deterministic state transitions for file transfers.
    
    Validates state updates and records transition timestamps to ensure transfer integrity.
    """
    
    # Map of valid source states to allowed destination states
    _VALID_TRANSITIONS = {
        TransferState.CREATED: {TransferState.UPLOADING, TransferState.EXPIRED},
        
        # UPLOADING can revert to CREATED (retry/reconnect safe) or advance
        TransferState.UPLOADING: {TransferState.UPLOADED, TransferState.CREATED, TransferState.EXPIRED},
        
        TransferState.UPLOADED: {TransferState.VERIFIED, TransferState.EXPIRED},
        TransferState.VERIFIED: {TransferState.READY, TransferState.EXPIRED},
        TransferState.READY: {TransferState.DOWNLOADED, TransferState.EXPIRED},
        TransferState.DOWNLOADED: set(),  # Terminal state
        TransferState.EXPIRED: set()     # Terminal state
    }
    
    @classmethod
    def can_transition(cls, current_state, new_state):
        """Checks if a transition from current_state to new_state is allowed."""
        if current_state not in cls._VALID_TRANSITIONS:
            return False
        return new_state in cls._VALID_TRANSITIONS[current_state]
        
    @classmethod
    def transition(cls, session_data, new_state):
        """Attempts to update a session's state, checking valid transitions and adding timestamps.
        
        Args:
            session_data (dict): The session record dictionary.
            new_state (str): The state to transition to.
            
        Returns:
            dict: The modified session data.
            
        Raises:
            ValueError: If the state transition violates rules.
        """
        current_state = session_data.get("status", TransferState.CREATED)
        
        # Check transition validity
        if not cls.can_transition(current_state, new_state):
            raise ValueError(
                f"Invalid transfer state transition: Cannot change from '{current_state}' to '{new_state}'"
            )
            
        # Update state and append transition metadata
        session_data["status"] = new_state
        session_data["timestamp"] = time.time()
        
        # Record specific milestones
        if "history" not in session_data:
            session_data["history"] = {}
            
        session_data["history"][new_state] = time.time()
        return session_data
