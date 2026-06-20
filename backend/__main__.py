"""Module entry point to run the Flask app with `python -m backend`.

Also supports running the file directly (`python backend/__main__.py`) by
falling back to an absolute import when the package context is missing.
"""
import os
import sys
try:
    # Preferred: run as package: `python -m backend`
    from . import create_app
except Exception:
    # Fallback: allow `python backend/__main__.py` (script mode)
    pkg_root = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(pkg_root)
    # Ensure project root is on sys.path so `import backend` resolves
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    # import the package module and get create_app
    import importlib
    create_app = importlib.import_module('backend').create_app


def run():
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    debug = app.config.get('DEBUG', False)
    app.run(host='0.0.0.0', port=port, debug=debug)


if __name__ == '__main__':
    run()
