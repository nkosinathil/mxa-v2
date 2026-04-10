"""Parser for WhatsApp PDF exports."""
import os
import re
from typing import List, Dict, Any
from .base import BaseParser
from ..utils import parse_timestamp
from ..categorizer import categorize_text

try:
    import pdfplumber
except Exception:
    pdfplumber = None
try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

TS_RE = re.compile(r'^(\d{4}[/-]\d{2}[/-]\d{2}\s+\d{2}:\d{2}(?::\d{2})?|\d{1,2}[/-]\d{1,2}[/-]\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s?[APMapm]{2})?)$')
FILE_RE = re.compile(r'\b[A-Za-z0-9_\-()]+\.[A-Za-z0-9]{2,6}\b')
SYSTEM_PATTERNS = [re.compile(r'end-to-end encrypted', re.I), re.compile(r'security code changed', re.I)]


def _extract_text(file_path: str) -> str:
    texts = []
    if pdfplumber is not None:
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    texts.append(page.extract_text() or '')
        except Exception:
            pass
    if not ''.join(texts).strip() and PdfReader is not None:
        try:
            reader = PdfReader(file_path)
            texts = [(page.extract_text() or '') for page in reader.pages]
        except Exception:
            pass
    return '\n'.join(texts).strip()


def _conversation_name(file_path: str, text: str) -> str:
    lines = [re.sub(r'\s+', ' ', x).strip() for x in text.splitlines() if x.strip()]
    for i, ln in enumerate(lines[:12]):
        if "'s WhatsApp" in ln:
            prefix = ln.replace("'s WhatsApp", '').strip()
            for cand in lines[i+1:i+4]:
                if re.match(r'^\+?\d[\d ]{6,}$', cand.strip()):
                    return cand.strip()
            return prefix or os.path.splitext(os.path.basename(file_path))[0]
    return os.path.splitext(os.path.basename(file_path))[0]


class WhatsAppPDFParser(BaseParser):
    def can_parse(self, file_path: str) -> bool:
        return file_path.lower().endswith('.pdf')

    def parse(self, file_path: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        text = _extract_text(file_path)
        if not text:
            return []
        low = text[:4000].lower()
        if 'whatsapp' not in low and '.opus' not in low and 'img-' not in low and 'ptt-' not in low:
            return []
        owner_name = context.get('owner_name') or context.get('device_owner') or 'You'
        chat_name = _conversation_name(file_path, text)
        direct_chat = bool(chat_name and re.search(r'\+?\d{7,15}', chat_name.replace(' ', '')))
        lines = [re.sub(r'\s+', ' ', x).strip() for x in text.splitlines() if x.strip()]
        results = []
        seq = 0
        i = 0
        last_direction = ''
        while i < len(lines):
            line = lines[i]
            if TS_RE.match(line):
                ts = parse_timestamp(line)
                if not ts:
                    i += 1
                    continue
                j = i + 1
                payload = []
                while j < len(lines) and not TS_RE.match(lines[j]):
                    payload.append(lines[j])
                    j += 1
                body = ' '.join(payload).strip()
                if body:
                    sender = ''
                    direction = ''
                    receiver = ''
                    m = re.match(r'^(You|Me|[^:]{2,80}):\s+(.*)$', body, re.I)
                    if m:
                        raw_sender = m.group(1).strip()
                        body = m.group(2).strip()
                        if raw_sender.lower() in {'you', 'me'} or raw_sender == owner_name:
                            sender = owner_name
                            direction = 'Outgoing'
                            receiver = chat_name
                        else:
                            sender = raw_sender
                            direction = 'Incoming'
                            receiver = owner_name if direct_chat else chat_name
                    else:
                        sender = owner_name if last_direction == 'Outgoing' else chat_name
                        direction = last_direction or 'Incoming'
                        receiver = chat_name if direction == 'Outgoing' else (owner_name if direct_chat else chat_name)
                    if any(p.search(body) for p in SYSTEM_PATTERNS):
                        direction = 'System'
                    media_name = ''
                    fm = FILE_RE.search(body)
                    if fm:
                        media_name = fm.group(0)
                    cat = categorize_text(body, context.get('category_config'))
                    results.append({
                        'mode': 'whatsapp', 'timestamp': ts.isoformat(sep=' ', timespec='minutes'),
                        'time': ts.strftime('%Y-%m-%d %H:%M'), 'date_str': ts.strftime('%Y-%m-%d %H:%M'),
                        'chat': chat_name, 'sender': sender, 'receiver': receiver, 'direction': direction,
                        'message': body, 'body': body, 'subject': '', 'category': cat, 'categories': [cat],
                        'conversation_key': chat_name, 'message_id': f'{chat_name}_{seq}', 'sequence_no': seq,
                        'attachment_name': media_name, 'attachment': media_name, 'source_file': file_path,
                    })
                    seq += 1
                    if direction in {'Incoming', 'Outgoing'}:
                        last_direction = direction
                i = j
            else:
                i += 1
        return results
