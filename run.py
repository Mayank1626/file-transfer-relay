import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    # Parse port and host settings from config
    port = app.config['PORT']
    debug = app.config['DEBUG']
    
    print(f"Booting ZapLink Core Relay in {'DEBUG' if debug else 'PRODUCTION'} mode on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=debug, threaded=True)
