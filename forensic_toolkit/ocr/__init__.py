"""Compatibility OCR package.

Exposes OCR helpers from the legacy flat module ``forensic_toolkit/ocr.py`` so the
package works whether imports resolve to a flat module or a package.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_module_path = Path(__file__).resolve().parent.parent / 'ocr.py'
_spec = importlib.util.spec_from_file_location('forensic_toolkit._ocr_flat', _module_path)
if _spec is None or _spec.loader is None:
    raise ImportError(f'Unable to load OCR module from {_module_path}')
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

ocr_image = _mod.ocr_image
IMAGE_EXTS = _mod.IMAGE_EXTS
is_image = getattr(_mod, 'is_image', None)
normalize = getattr(_mod, 'normalize', None)

__all__ = ['ocr_image', 'IMAGE_EXTS', 'is_image', 'normalize']
