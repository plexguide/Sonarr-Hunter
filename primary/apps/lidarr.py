from flask import Blueprint, jsonify

lidarr_bp = Blueprint('lidarr', __name__)

@lidarr_bp.route('/placeholder', methods=['GET'])
def placeholder():
    # Placeholder for future Lidarr functionality
    return jsonify({"message": "Lidarr functionality coming soon"})
