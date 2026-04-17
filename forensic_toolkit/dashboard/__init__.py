"""Compatibility dashboard package.

Exposes generate_dashboard from the legacy flat module ``forensic_toolkit/dashboard.py``
so imports keep working even when a stale or current ``dashboard/`` package exists.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_module_path = Path(__file__).resolve().parent.parent / 'dashboard.py'
_spec = importlib.util.spec_from_file_location('forensic_toolkit._dashboard_flat', _module_path)
if _spec is None or _spec.loader is None:
    raise ImportError(f'Unable to load dashboard module from {_module_path}')
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

generate_dashboard = _mod.generate_dashboard
IMAGE_EXTENSIONS = getattr(_mod, 'IMAGE_EXTENSIONS', set())

__all__ = ['generate_dashboard', 'IMAGE_EXTENSIONS']
