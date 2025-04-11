from flask import Blueprint, jsonify

readarr_bp = Blueprint('readarr', __name__)

@readarr_bp.route('/placeholder', methods=['GET'])
def placeholder():
    # Placeholder for future Readarr functionality
    return jsonify({"message": "Readarr functionality coming soon"})
