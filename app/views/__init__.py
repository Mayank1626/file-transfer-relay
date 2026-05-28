from flask import Blueprint

views_bp = Blueprint('views', __name__)

# Import views to register routes on the blueprint
from app.views import main
