"""Compatibility wrapper for backend model utilities.

This module keeps legacy imports working from project root while delegating to
backend.models where the implementation lives.
"""

from backend.models import *  # noqa: F401,F403
