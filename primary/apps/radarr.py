from flask import Blueprint, jsonify

radarr_bp = Blueprint('radarr', __name__)

@radarr_bp.route('/placeholder', methods=['GET'])
def placeholder():
    # Placeholder for future Radarr functionality
    return jsonify({"message": "Radarr functionality coming soon"})
