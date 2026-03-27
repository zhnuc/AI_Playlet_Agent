"""Compatibility entrypoint for uvicorn: `uvicorn api:app`."""

from backend.app_factory import create_app

app = create_app()

