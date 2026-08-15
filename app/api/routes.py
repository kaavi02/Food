from flask import jsonify
from app.api import api

@api.route('/status')
def status():
    return jsonify({"status": "ok"})
