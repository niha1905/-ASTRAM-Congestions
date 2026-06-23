"""Mappls configuration endpoints for the frontend SDK."""

from flask import Blueprint, jsonify

from ..mappls_client import MAPPLS_WEB_SDK_KEY, get_mappls_access_token, is_mappls_configured

mappls_bp = Blueprint('mappls', __name__, url_prefix='/api/mappls')


def _mappls_config_payload():
    if not is_mappls_configured():
        return None, (
            jsonify({
                'configured': False,
                'access_token': None,
                'sdk_key': None,
                'error': 'Mappls credentials are not configured on the backend',
            }),
            503,
        )

    bearer = get_mappls_access_token()
    sdk_key = (MAPPLS_WEB_SDK_KEY or '').strip()
    script_token = bearer or sdk_key

    if not script_token:
        return None, (
            jsonify({
                'configured': True,
                'access_token': None,
                'sdk_key': None,
                'error': 'Unable to obtain Mappls bearer token or SDK key',
            }),
            503,
        )

    return {
        'configured': True,
        'access_token': script_token,
        'sdk_key': sdk_key or None,
    }, None


@mappls_bp.route('/config', methods=['GET'])
def mappls_config():
    """Return bearer token for advancedmaps SDK script URL (see Mappls Web JS docs)."""
    payload, error = _mappls_config_payload()
    if error:
        return error
    return jsonify(payload)


@mappls_bp.route('/token', methods=['GET'])
def mappls_token():
    """Backward-compatible alias for /config."""
    payload, error = _mappls_config_payload()
    if error:
        return error
    return jsonify(payload)
