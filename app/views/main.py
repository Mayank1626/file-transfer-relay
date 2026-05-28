from flask import render_template
from app.views import views_bp

@views_bp.route('/', methods=['GET'])
def index():
    """Renders the main ZapLink pairing user interface page."""
    return render_template('index.html')
