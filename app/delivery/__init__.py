from flask import Blueprint

delivery = Blueprint('delivery', __name__)

from . import routes
