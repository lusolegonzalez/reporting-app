from flask import Blueprint, jsonify


reports_bp = Blueprint("reports", __name__)


@reports_bp.get("")
def list_reports_placeholder():
    return jsonify({"items": [], "message": "Listado placeholder de reportes"}), 200


@reports_bp.get("/<int:report_id>")
def get_report_placeholder(report_id: int):
    return jsonify({"id": report_id, "message": "Detalle placeholder de reporte"}), 200
