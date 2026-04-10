MxA Qt GUI package updated with bundled Roboto fonts and premium spacing.

Changes:
- Added Roboto static fonts under forensic_toolkit/gui_assets/fonts/roboto
- GUI now loads Roboto at startup using QFontDatabase
- Global font family changed from Segoe UI to Roboto
- Added premium spacing, control padding, refined weights, and dark styling updates
- Uses Roboto Regular for body text, Medium/SemiBold/Bold where Qt weight rules apply

Run:
python -m forensic_toolkit.gui


Qt dependency note:
- Preferred binding: PySide6
- Install dependencies with: pip install -r forensic_toolkit/requirements.txt
- The GUI falls back in this order: PySide6 -> PyQt6 -> PyQt5
