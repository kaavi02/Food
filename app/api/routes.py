from flask import jsonify, current_app
from app.api import api
from app import db
from sqlalchemy import text
from datetime import datetime
import time

@api.route('/keep-alive', methods=['GET', 'HEAD'])
@api.route('/health', methods=['GET', 'HEAD'])
@api.route('/status', methods=['GET', 'HEAD'])
@api.route('/ping', methods=['GET', 'HEAD'])
def keep_alive():
    """
    Dedicated Keep-Alive & Health Check Endpoint for Cron Jobs (e.g. cron-job.org).
    Executes a fast ping against the database to keep connection pools alive and prevent cloud DB pausing.
    """
    start_time = time.time()
    db_status = "connected"
    error_msg = None
    
    try:
        # Ping the MySQL database with a lightweight scalar query
        result = db.session.execute(text("SELECT 1")).scalar()
        if result != 1:
            db_status = "unexpected_result"
    except Exception as e:
        db.session.rollback()
        db_status = "error"
        error_msg = str(e)
        current_app.logger.error(f"Keep-alive DB ping failed: {e}")

    latency_ms = round((time.time() - start_time) * 1000, 2)
    
    status_code = 200 if db_status == "connected" else 500
    
    response = {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "service": "Kavi's Quick Bite",
        "database": db_status,
        "latency_ms": latency_ms,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "message": "Database and serverless instance are active." if db_status == "connected" else "Database connection issue."
    }
    
    if error_msg:
        response["error"] = error_msg

    return jsonify(response), status_code
