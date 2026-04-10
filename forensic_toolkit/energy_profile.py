#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
energy_profile.py — Optional, switchable profile for Public Utility (Energy) investigations.

Purpose
-------
Provides ENERGY-specific heuristics that can be *enabled* or *disabled* without polluting
the generic pipelines. When enabled, modules may:
- Score/flag Energy-related keywords in messages/transcripts.
- Enable meter/transformer heuristics in vision.
- Inject "Energy Findings" sections/columns in reports.

How it toggles ON
-----------------
1) CLI flag (recommended): pass --profile energy (or --enable-energy) to your tools.
   Use add_cli_args(parser) + resolve_from_args(args) helpers.
2) Environment: set PROFILE=energy OR ENABLE_ENERGY=1/true/yes.

Usage in a tool
---------------
try:
    import energy_profile as ENERGY
except Exception:
    ENERGY = None

energy_on = ENERGY.is_enabled_from_env()
cfg = ENERGY.get_config() if energy_on else None

# Example: scan a text
hits = ENERGY.scan_text("Found transformer near substation; STS token 123456")
if hits['count']:
    print("Energy hits:", hits['matches'])

# Example: argparse integration
#   p = argparse.ArgumentParser(...)
#   ENERGY.add_cli_args(p)
#   args = p.parse_args()
#   energy_on = ENERGY.resolve_from_args(args)  # also honors env vars

Author: Governance Intelligence (Pty) Ltd — Forensic AI Assistant
"""
from __future__ import annotations
import os, re, json
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Iterable

# -------------------- Vocabulary --------------------
# Minimal, extensible seed list. You can add to this list or load external packs.
ENERGY_KEYWORDS: List[str] = [
    # Core assets / infra
    "transformer", "mini-sub", "minisub", "substation", "switchgear", "feeder", "pole", "pylon",
    "distribution box", "db board", "dbboard", "distribution board", "kiosk",
    "overhead line", "conductor", "mv cable", "lv cable",
    # Metering / tokens / tamper
    "meter", "prepaid", "token", "sts", "kwh", "kilowatt-hour", "kva", "ct", "vt",
    "bypass", "bridging", "illegal connection", "hook", "jumpers",
    # Work orders / ops
    "outage", "load shedding", "trip", "earth fault", "fault", "isolation", "reclose",
    "work order", "job card", "call-out", "disconnection", "reconnection",
    # Payments / screenshots (local context examples)
    "eskom", "city power", "municipality", "prepaid voucher",
    # Visual cues in screenshots
    "meter number", "serial", "active energy", "reactive energy", "phase", "single phase", "three phase"
]

# Optional regex patterns (case-insensitive). Compiled on first use.
ENERGY_REGEXES_RAW: List[str] = [
    r"meter\s*(no\.?|number)\s*[:\-]?\s*\d{6,}",
    r"sts\s*token\s*[:\-]?\s*\d{6,}",
    r"\b(kwh|kva|kv|amp|amps|amperes)\b",
    r"\billegal\s+connection\b",
    r"\b(bypass|bridg(e|ing))\b",
    r"\b(sub\s?station|min[i\-]sub)\b",
]

# Vision label hints that can be preferred/promoted when ENERGY profile is on.
VISION_HINT_LABELS: List[str] = [
    "electricity_meter", "digital_electricity_meter", "analog_electricity_meter",
    "power_transformer", "distribution_transformer", "electric_pole", "power_line"
]

# -------------------- Internal state --------------------
_TRUE = {"1", "true", "yes", "on", "enable", "enabled"}

def _env_truth(name: str) -> bool:
    val = os.getenv(name, "")
    return val.strip().lower() in _TRUE

@dataclass(frozen=True)
class EnergyConfig:
    name: str = "public_utility_energy"
    keywords: List[str] = None
    regexes: List[re.Pattern] = None
    vision_hints: List[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "keywords": self.keywords or [],
            "regexes": [r.pattern for r in (self.regexes or [])],
            "vision_hints": self.vision_hints or [],
        }

# Singleton-like compiled regex cache
_REGEX_CACHE: Optional[List[re.Pattern]] = None

def _compiled_regexes() -> List[re.Pattern]:
    global _REGEX_CACHE
    if _REGEX_CACHE is None:
        _REGEX_CACHE = [re.compile(p, re.IGNORECASE) for p in ENERGY_REGEXES_RAW]
    return _REGEX_CACHE

# -------------------- Toggle logic --------------------
def is_enabled_from_env() -> bool:
    """
    Check environment variables only.
    Active if PROFILE=energy/public_utility_energy OR ENABLE_ENERGY ∈ {1,true,yes,on}.
    """
    profile = os.getenv("PROFILE", "").strip().lower()
    if profile in {"energy", "public_utility_energy"}:
        return True
    if _env_truth("ENABLE_ENERGY"):
        return True
    return False

def is_enabled(profile: Optional[str] = None, flag: Optional[bool] = None) -> bool:
    """
    General resolver:
      - If explicit boolean flag provided, use it.
      - Else if explicit profile name provided, check it.
      - Else fall back to environment.
    """
    if flag is not None:
        return bool(flag)
    if profile:
        p = str(profile).strip().lower()
        return p in {"energy", "public_utility_energy"}
    return is_enabled_from_env()

# -------------------- Argparse helpers --------------------
def add_cli_args(parser) -> None:
    """
    Injects common profile toggles into an argparse.ArgumentParser.
    """
    parser.add_argument("--profile",
                        choices=["generic", "energy", "public_utility_energy"],
                        help="Select an optional industry profile.")
    parser.add_argument("--enable-energy", action="store_true",
                        help="Shortcut to enable Public Utility – Energy profile.")

def resolve_from_args(args) -> bool:
    """
    Returns True if ENERGY should be enabled given parsed args and env.
    Also normalizes PROFILE env var for child processes.
    """
    on = False
    if getattr(args, "enable_energy", False):
        on = True
    elif getattr(args, "profile", None):
        on = args.profile in ("energy", "public_utility_energy")
    else:
        on = is_enabled_from_env()

    # Normalize env for subprocesses (Qt runner can call this before spawn)
    os.environ["PROFILE"] = "public_utility_energy" if on else os.environ.get("PROFILE", "generic")
    if on:
        os.environ["ENABLE_ENERGY"] = "1"
    return on

# -------------------- Config access --------------------
def get_config() -> EnergyConfig:
    return EnergyConfig(
        keywords=ENERGY_KEYWORDS[:],
        regexes=_compiled_regexes(),
        vision_hints=VISION_HINT_LABELS[:],
    )

# -------------------- Scanning utilities --------------------
def _norm_text(t: Optional[str]) -> str:
    return (t or "").lower()

def scan_text(text: Optional[str]) -> Dict[str, Any]:
    """
    Returns {'count': int, 'matches': List[str], 'regex_hits': List[str]}
    Safe if ENERGY is disabled (still returns matches; caller decides to use it).
    """
    t = _norm_text(text)
    if not t:
        return {"count": 0, "matches": [], "regex_hits": []}

    kw_hits = sorted({kw for kw in ENERGY_KEYWORDS if kw.lower() in t})
    re_hits = []
    for rgx in _compiled_regexes():
        m = rgx.search(t)
        if m:
            re_hits.append(m.group(0))

    return {"count": len(kw_hits) + len(re_hits), "matches": kw_hits, "regex_hits": re_hits}

def any_hit(text: Optional[str]) -> bool:
    h = scan_text(text)
    return h["count"] > 0

def scan_many(texts: Iterable[str]) -> Dict[str, Any]:
    agg_matches, agg_regex = set(), []
    total = 0
    for t in texts or []:
        res = scan_text(t)
        total += res["count"]
        agg_matches |= set(res["matches"])
        agg_regex.extend(res["regex_hits"])
    return {"count": total, "matches": sorted(agg_matches), "regex_hits": agg_regex}

# -------------------- Vision helpers --------------------
def want_meter_heuristics(enabled: Optional[bool] = None) -> bool:
    return is_enabled(flag=enabled)

def promote_label_if_energy(top_label: str, top_conf: float, ocr_text: str,
                            shape_score: float, is_screenshot: bool) -> Dict[str, Any]:
    """
    If ENERGY is on, apply gentle fusion of OCR keyword hits + shape hints to promote meter labels.
    Returns possibly adjusted {'label': str, 'conf': float}.
    Caller keeps its own thresholds/clamps.
    """
    if not is_enabled():
        return {"label": top_label, "conf": top_conf}

    hits = scan_text(ocr_text)
    fused = min(1.0, (hits["count"] / 3.0) * 0.7 + max(0.0, shape_score) * 0.3)
    if is_screenshot:
        return {"label": top_label, "conf": top_conf}

    if ("meter" in (top_label or "").lower() and top_conf >= 0.60) or fused >= 0.60:
        new_label = "digital_electricity_meter" if shape_score >= 0.35 else "electricity_meter"
        return {"label": new_label, "conf": max(top_conf, fused, 0.60)}
    return {"label": top_label, "conf": top_conf}

# -------------------- Reporting helpers --------------------
def profile_badge() -> str:
    return "Profile: Public Utility – Energy" if is_enabled() else "Profile: Generic"

def inject_report_section(report_html_path: str, findings: List[Dict[str, Any]]) -> None:
    """
    Append a simple Energy Findings section to an existing HTML file.
    Safe no-op if ENERGY is disabled or no findings.
    """
    if not is_enabled() or not findings:
        return
    rows = []
    for i, f in enumerate(findings, start=1):
        what = (f.get("what") or "").replace("<","&lt;").replace(">","&gt;")
        src  = (f.get("src") or "").replace("<","&lt;").replace(">","&gt;")
        ctx  = (f.get("context") or "").replace("<","&lt;").replace(">","&gt;")
        rows.append(f"<tr><td>{i}</td><td>{what}</td><td>{ctx}</td><td>{src}</td></tr>")
    block = f"""
<!-- ENERGY PROFILE: auto-injected -->
<section style="margin-top:24px">
  <h2 style="margin:0 0 8px">Energy Findings</h2>
  <table style="width:100%;border-collapse:collapse;font:14px/1.4 Arial">
    <thead>
      <tr style="text-align:left;border-bottom:2px solid #e5e7eb">
        <th style="padding:8px">#</th><th style="padding:8px">What</th>
        <th style="padding:8px">Context</th><th style="padding:8px">Source</th>
      </tr>
    </thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</section>
"""
    try:
        with open(report_html_path, "a", encoding="utf-8") as f:
            f.write(block)
    except Exception:
        pass
