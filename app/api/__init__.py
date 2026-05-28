from flask import Blueprint

api_bp = Blueprint('api', __name__)

# Import controllers to register routes on the blueprint
from app.api import pins, transfer, stats
