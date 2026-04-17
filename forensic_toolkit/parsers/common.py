import hashlib
import os
import re
from typing import Any, Dict

from ..categorizer import classify_text, load_category_config
from ..utils import parse_timestamp


def clean_text(value: Any) -> str:
    if value is None:
        return ''
    value = str(value).replace('\r', ' ').replace('\n', ' ').replace('\t', ' ')
    value = re.sub(r'\s+', ' ', value)
    return value.strip()


def clean_phone(value: Any) -> str:
    text = clean_text(value)
    text = text.replace('"', '')
    text = re.sub(r'\s+', '', text)
    return text


def record_id(*parts: Any) -> str:
    payload = '||'.join(str(p or '') for p in parts)
    return hashlib.sha256(payload.encode('utf-8', errors='ignore')).hexdigest()[:32]


def enrich_categories(record: Dict[str, Any], package_dir: str, case_dir: str = None) -> Dict[str, Any]:
    rules = load_category_config(package_dir=package_dir, extra_dir=os.path.join(case_dir, 'config', 'categories') if case_dir else None)
    text = ' '.join([
        str(record.get('subject', '')),
        str(record.get('message', '')),
        str(record.get('body', '')),
        str(record.get('ocr_text', '')),
    ])
    labels, matched, primary = classify_text(text, rules)
    record['categories'] = labels
    record['category'] = primary
    record['matched_keywords'] = matched
    return record


def base_record(mode: str, source_file: str, timestamp, sender: str, receiver: str, message: str, attachment_name: str = '', **extra) -> Dict[str, Any]:
    ts = parse_timestamp(str(timestamp)) if not hasattr(timestamp, 'strftime') else timestamp
    date_str = ts.strftime('%Y-%m-%d %H:%M') if ts else str(timestamp or '')
    rec = {
        'id': record_id(mode, source_file, date_str, sender, receiver, message, attachment_name),
        'mode': mode,
        'source_file': source_file,
        'source_path': source_file,
        'timestamp': date_str,
        'time': date_str,
        'date_str': date_str,
        'chat': '',
        'sender': sender or '',
        'receiver': receiver or '',
        'direction': '',
        'message': message or '',
        'body': message or '',
        'subject': '',
        'category': 'All items',
        'categories': ['All items'],
        'conversation_key': '',
        'chat_type': '',
        'attachment_name': attachment_name or '',
        'attachment': attachment_name or '',
        'attachment_path': '',
        'media_path': '',
        'media_exists': False,
        'media_deleted': False,
        'message_kind': 'text',
        'ocr_text': '',
        'duration': '',
        'attachment_count': 1 if attachment_name else 0,
    }
    rec.update(extra)
    if not rec['conversation_key']:
        rec['conversation_key'] = rec.get('chat') or sender or receiver or mode
    return rec
