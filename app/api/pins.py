import time
import random
from flask import jsonify, current_app
from app.api import api_bp
from app.sessions import get_sessions
from app.utils.state_machine import TransferState, TransferStateMachine
from app.middleware.security import get_limiter

# Get limiter decorator or create dummy if rate limiting is off
limiter = get_limiter()
limit_decorator = limiter.limit(current_app.config['RATELIMIT_PIN_REQUEST']) if limiter else lambda x: x

def generate_pin(sessions):
    """Generates a unique 6-digit PIN."""
    while True:
        pin = str(random.randint(100000, 999999))
        if not sessions.exists(pin):
            return pin

@api_bp.route('/request-pin', methods=['GET'])
def request_pin():
    """Generates a pairing PIN and initializes the transfer session."""
    sessions = get_sessions()
    
    # Increment total upload stats metric
    if hasattr(sessions, 'increment_stat'):
        sessions.increment_stat("stats:total_uploads")
        
    pin = generate_pin(sessions)
    
    # Structure initial session dictionary matching state machine
    session_data = {
        'filename': None,
        'filepath': None,
        'timestamp': time.time(),
        'status': TransferState.CREATED,
        'history': {TransferState.CREATED: time.time()}
    }
    
    sessions.save_session(pin, session_data)
    current_app.logger.info(f"Initialized pairing session with PIN: {pin}")
    return jsonify({'pin': pin})
