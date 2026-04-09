import json, os, re, importlib
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple, Iterable, Any

DEFAULT_CONFIG = {
    "categories": [
        {"name": "All items", "keywords": [], "match_mode": "all", "priority": 9999},
        {"name": "Personal", "keywords": [
            "family", "wife", "husband", "child", "home", "birthday", "funeral", "love", "friend",
            "mother", "father", "school", "house", "visit", "baby", "wedding", "weekend"
        ], "match_mode": "any", "priority": 50},
        {"name": "Promotional", "keywords": [
            "special", "discount", "sale", "promotion", "offer", "buy now", "limited", "subscribe",
            "deal", "advert", "free delivery", "promo", "clearance", "exclusive"
        ], "match_mode": "any", "priority": 60}
    ]
}

MODEL_FILE_MAP = {
    "generic": None,
    "default": None,
    "energy": "energy.json",
    "banking": "banking.json",
    "finance": "banking.json",
    "procurement": "scm.json",
    "scm": "scm.json",
    "supplychain": "scm.json",
    "utilities": "energy.json",
}

WORD_RE = re.compile(r"\b\w+[\w-]*\b", re.UNICODE)
_BAD_SINGLETONS = {"a", "e", "i", "l", "m"}
_GENERIC_ALLOWED = {"personal", "promotional"}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def clean_category_name(value: Any) -> str:
    """
    Normalize category values and suppress bad one-character artifacts such as:
    A, e, i, l, m. Keep only meaningful display names.
    """
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) <= 1 or text.lower() in _BAD_SINGLETONS:
        return ""
    # collapse whitespace, preserve title case style already used in configs
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_category_list(values: Any, fallback: str = "Personal") -> List[str]:
    """
    Accept a list/tuple/set or comma-separated string and return a clean list
    of category names. This prevents strings from being joined character-by-character.
    """
    raw_parts: List[str] = []
    if values is None:
        raw_parts = []
    elif isinstance(values, (list, tuple, set)):
        raw_parts = [str(v or "") for v in values]
    else:
        text = str(values or "")
        # split only on commas/semicolons/pipes/newlines; never on individual chars
        raw_parts = re.split(r"[,;|\n]+", text)

    cleaned: List[str] = []
    seen = set()
    for part in raw_parts:
        name = clean_category_name(part)
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(name)

    if not cleaned and fallback:
        cleaned = [fallback]
    return cleaned


def enforce_generic_categories(categories: List[str]) -> List[str]:
    """
    The Generic model should only yield Personal and Promotional. Any invalid
    category artifacts are discarded here.
    """
    out: List[str] = []
    seen = set()
    for name in categories or []:
        key = str(name or "").strip().lower()
        if key in _GENERIC_ALLOWED and key not in seen:
            seen.add(key)
            out.append("Personal" if key == "personal" else "Promotional")
    return out


def clean_generic_result(primary: str, labels: List[str]) -> Tuple[str, List[str]]:
    cleaned = normalize_category_list(labels, fallback="Personal")
    cleaned = [c for c in cleaned if c.lower() != "all items"]
    generic_only = enforce_generic_categories(cleaned)
    if generic_only:
        cleaned = generic_only
    if not cleaned:
        cleaned = ["Personal"]
    if primary and clean_category_name(primary).lower() == "promotional":
        primary = "Promotional"
    elif primary and clean_category_name(primary).lower() == "personal":
        primary = "Personal"
    else:
        primary = cleaned[0]
    return primary, cleaned


def _merge_category_sets(base_categories: List[Dict], extra_categories: Iterable[Dict]) -> List[Dict]:
    categories = [dict(c) for c in (base_categories or [])]
    seen = {c.get("name"): c for c in categories if c.get("name")}
    for cat in extra_categories or []:
        name = clean_category_name((cat or {}).get("name"))
        if not name:
            continue
        if name in seen:
            old = seen[name]
            old_keywords = set(old.get("keywords", []) or [])
            old["keywords"] = sorted(old_keywords | set(cat.get("keywords", []) or []))
            if "priority" in cat and cat.get("priority") is not None:
                old["priority"] = min(old.get("priority", 9999), cat.get("priority", 9999))
            if cat.get("match_mode"):
                old["match_mode"] = cat.get("match_mode")
        else:
            clone = dict(cat)
            clone["name"] = name
            categories.append(clone)
            seen[name] = clone
    categories.sort(key=lambda c: (c.get("priority", 9999), c.get("name", "")))
    return categories


def _read_json_categories(path: Path) -> List[Dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    return data.get("categories", []) or []


def load_category_config(package_dir: str = None, extra_dir: str = None, selected_models: List[str] = None) -> Dict:
    selected = [str(x).strip().lower() for x in (selected_models or []) if str(x).strip()]
    if not selected:
        selected = ["generic"]
    if "generic" not in selected:
        selected.insert(0, "generic")

    categories: List[Dict] = []
    if package_dir:
        default_file = Path(package_dir) / "config" / "message_categories.json"
        categories = _read_json_categories(default_file)
    if not categories:
        categories = [dict(c) for c in DEFAULT_CONFIG["categories"]]

    if package_dir:
        model_dir = Path(package_dir) / "config" / "models"
        for model_name in selected:
            fname = MODEL_FILE_MAP.get(model_name)
            if not fname:
                continue
            categories = _merge_category_sets(categories, _read_json_categories(model_dir / fname))

    if extra_dir and os.path.isdir(extra_dir):
        for fname in sorted(os.listdir(extra_dir)):
            if not fname.lower().endswith('.json'):
                continue
            categories = _merge_category_sets(categories, _read_json_categories(Path(extra_dir) / fname))

    return {"categories": categories, "selected_models": selected}



def _industry_rule_hits(text: str, selected_models: List[str]) -> List[str]:
    models = {str(m or '').strip().lower() for m in (selected_models or [])}
    if not models:
        return []
    out: List[str] = []
    def add(name: str):
        clean = clean_category_name(name)
        if clean and clean not in out:
            out.append(clean)
    hay = _norm(text)
    # banking
    if models & {"banking", "finance"}:
        banking_groups = {
            "Banking": ["bank", "banking", "account", "payment", "transfer", "deposit", "withdrawal", "transaction", "beneficiary", "bank details", "banking details", "statement", "balance", "card", "atm", "swift", "iban", "eft", "otp"],
            "Payments": ["payment", "paid", "eft", "settlement", "proof of payment", "pop"],
            "Accounts": ["account", "account number", "balance", "statement", "bank account"],
            "Transfers": ["transfer", "wire", "swift", "iban", "send money", "receive money"],
            "Cards": ["card", "atm", "pin", "credit card", "debit card"],
            "Fraud": ["otp", "one time pin", "phishing", "scam", "unauthorized", "bank detail change", "beneficiary change", "account change"],
        }
        bank_hit = False
        for label, kws in banking_groups.items():
            if any(_norm(k) in hay for k in kws):
                if label == "Banking":
                    bank_hit = True
                add(label)
        if bank_hit:
            add("Banking")
    # energy
    if models & {"energy", "utilities"}:
        energy_labels = []
        try:
            mod = importlib.import_module('.energy_profile', __package__)
            hits = mod.scan_text(text or '') or {}
            if hits.get('count'):
                add('Energy / Utilities')
                matches = {str(m).lower() for m in (hits.get('matches') or [])}
                if any(m in matches for m in ['meter','prepaid','token','sts','meter number','serial','active energy','reactive energy','single phase','three phase']):
                    add('Metering')
                if any(m in matches for m in ['illegal connection','bypass','bridging','hook','jumpers']):
                    add('Illegal Connections')
                if any(m in matches for m in ['transformer','substation','switchgear','feeder','pole','pylon','distribution box','distribution board','overhead line','mv cable','lv cable']):
                    add('Infrastructure')
                if any(m in matches for m in ['outage','load shedding','trip','earth fault','fault','isolation','reclose','work order','job card','call-out','disconnection','reconnection']):
                    add('Operations')
        except Exception:
            pass
    # scm
    if models & {"procurement", "scm", "supplychain"}:
        try:
            mod = importlib.import_module('.scm_risk_model', __package__)
            assessment = mod.deterministic_procurement_assessment(text or '') or {}
            indicators = assessment.get('risk_indicators') or []
            stage = str(assessment.get('scm_stage') or '')
            if stage and stage != 'Not procurement-related' or indicators:
                add('SCM')
                if any(x in hay for x in ['quotation','quote','rfq','rfx','three quotes','limited quotes','single quote']):
                    add('Quotations')
                if any(x in hay for x in ['supplier','vendor','contractor','beneficiary','preferred supplier','registered address']):
                    add('Vendors')
                if any(x in hay for x in ['contract','agreement','tender','award','adjudication','variation','extension','addendum']):
                    add('Contracts')
                if any(x in hay for x in ['delivery','shipment','stock','goods received','grn','pod','proof of delivery','delivery note']):
                    add('Logistics')
                if any(('fraud' in ind.lower()) or ('collusion' in ind.lower()) or ('conflict of interest' in ind.lower()) for ind in indicators):
                    add('Fraud & Collusion')
        except Exception:
            pass
    return out

def classify_text(text: str, config: Dict) -> Tuple[List[str], Dict[str, List[str]], str]:
    hay = _norm(text)
    labels = ["All items"]
    matched = {"All items": []}
    primary = "All items"
    best_priority = 9999

    for cat in config.get('categories', []):
        name = clean_category_name(cat.get('name') or '')
        if not name or name == 'All items':
            continue
        kws = [k for k in cat.get('keywords', []) if k]
        mode = (cat.get('match_mode') or 'any').lower()
        found = []
        for kw in kws:
            nkw = _norm(kw)
            if not nkw:
                continue
            if nkw in hay:
                found.append(kw)
        ok = False
        if mode == 'all' and kws:
            ok = len(found) == len(kws)
        elif mode == 'any':
            ok = bool(found)
        if ok:
            labels.append(name)
            matched[name] = found
            pr = cat.get('priority', 9999)
            if pr < best_priority:
                best_priority = pr
                primary = name

    selected_models = [str(x).strip().lower() for x in (config.get("selected_models") or []) if str(x).strip()]
    domain_hits = _industry_rule_hits(text, selected_models)
    for hit in domain_hits:
        if hit not in labels:
            labels.append(hit)
            matched.setdefault(hit, [])
    if domain_hits:
        preferred = domain_hits[0]
        primary = preferred
        cleaned_labels = normalize_category_list(labels, fallback=preferred)
        cleaned_labels = [c for c in cleaned_labels if c.lower() != 'all items']
    else:
        primary, cleaned_labels = clean_generic_result(primary, labels)
    # Keep the internal umbrella for search-all semantics, but never return junk categories.
    return ["All items"] + [c for c in cleaned_labels if c != "All items"], matched, primary


def suggest_category_json(records: List[dict], top_n: int = 25) -> Dict:
    counts = Counter()
    stop = {
        'the', 'and', 'for', 'that', 'this', 'with', 'you', 'your', 'from', 'have', 'are', 'was', 'were', 'not',
        'but', 'all', 'can', 'our', 'has', 'had', 'will', 'would', 'shall', 'they', 'their', 'them', 'his', 'her'
    }
    for r in records:
        text = ' '.join([
            str(r.get('subject', '')),
            str(r.get('message', '')),
            str(r.get('body', '')),
            str(r.get('ocr_text', '')),
        ])
        for word in WORD_RE.findall(_norm(text)):
            if len(word) < 4 or word in stop or word.isdigit():
                continue
            counts[word] += 1
    top_keywords = [w for w, _ in counts.most_common(top_n)]
    return {
        'categories': [
            {
                'name': 'Custom Category',
                'keywords': top_keywords,
                'match_mode': 'any',
                'priority': 100
            }
        ]
    }


def categorize_text(text: str, config: dict = None) -> str:
    cfg = config or load_category_config()
    labels, matched, primary = classify_text(text, cfg)
    return clean_category_name(primary) or "Personal"
