import os
import re
import mailbox
from pathlib import Path
from zipfile import ZipFile, BadZipFile

from bs4 import BeautifulSoup
import pandas as pd
from email import message_from_binary_file
from .utils import detect_encoding, parse_timestamp, pick_datetime_col, slugify

try:
    import extract_msg
    MSG_SUPPORT = True
except Exception:
    MSG_SUPPORT = False

try:
    import pdfplumber
except Exception:
    pdfplumber = None

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

TEXT_HINT_COLS = {'message', 'content', 'body', 'text', 'sms', 'mms', 'snippet'}
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp', '.heic', '.heif', '.gif'}
CHAT_LINE_PATTERNS = [
    re.compile(r'^(?P<ts>\d{4}[/-]\d{2}[/-]\d{2}\s+\d{1,2}:\d{2}(?::\d{2})?)\s*(?:(?P<sender>[^:]{1,80}):\s*)?(?P<body>.+)$'),
    re.compile(r'^\[?(?P<ts>\d{1,2}[/-]\d{1,2}[/-]\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s?[APMapm]{2})?)\]?\s*[-–—]?\s*(?:(?P<sender>[^:]{1,80}):\s*)?(?P<body>.+)$'),
]
ATTACHMENT_NAME_PAT = re.compile(r'(?P<name>[A-Za-z0-9_\-]+\.(?:jpg|jpeg|png|gif|bmp|webp|heic|heif|opus|ogg|mp3|wav|m4a|mp4|mov|avi|pdf|docx?|xlsx?|pptx?))', re.I)


def read_table(path):
    if path.lower().endswith('.xlsx'):
        return pd.read_excel(path, engine='openpyxl')
    return pd.read_csv(path, encoding=detect_encoding(path))


def detect_table_mode(df: pd.DataFrame):
    cols = {c.lower() for c in df.columns}
    call_hits = len(cols & {'call type', 'direction', 'duration', 'duration(s)', 'call duration'})
    text_hits = len(cols & {'message', 'content', 'body', 'text', 'sms', 'mms', 'snippet'})
    if call_hits > text_hits:
        return 'calls'
    if text_hits:
        return 'texts'
    return None


def parse_calls_table(path):
    df = read_table(path)
    if detect_table_mode(df) != 'calls':
        return []
    out = []
    date_col = next((c for c in ['Date', 'date', 'Time', 'Timestamp', 'Call Time', 'Date/Time'] if c in df.columns), None) or pick_datetime_col(df)
    if not date_col:
        return out
    type_col = next((c for c in ['Type', 'type', 'Call Type', 'Direction'] if c in df.columns), None)
    name_col = next((c for c in ['Name', 'name', 'Contact', 'Caller Name'] if c in df.columns), None)
    number_col = next((c for c in ['Number', 'number', 'Phone', 'Phone Number', 'Address'] if c in df.columns), None)
    dur_col = next((c for c in ['Duration', 'duration', 'Duration(s)', 'Duration (s)', 'Call Duration'] if c in df.columns), None)
    for _, r in df.iterrows():
        ts = parse_timestamp(str(r.get(date_col)))
        if not ts:
            continue
        dur = r.get(dur_col, '') if dur_col else ''
        try:
            dur = int(str(dur).split('.')[0])
        except Exception:
            dur = ''
        out.append({
            'mode': 'calls', 'source_file': path, 'timestamp': ts.isoformat(sep=' '), 'date_str': ts.strftime('%Y-%m-%d %H:%M'),
            'sender': str(r.get(name_col, '')).strip() if name_col else '',
            'receiver': str(r.get(number_col, '')).strip() if number_col else '',
            'direction': str(r.get(type_col, '')).strip() if type_col else '',
            'chat': '', 'subject': '',
            'message': f'Call duration: {dur} sec' if dur != '' else '',
            'body': '', 'attachment_count': 0, 'meta': {'duration_sec': dur}
        })
    return out


def parse_texts_table(path):
    df = read_table(path)
    if detect_table_mode(df) != 'texts':
        return []
    out = []
    date_col = next((c for c in ['Date', 'date', 'Created', 'Timestamp', 'Time', 'Message Date/Time', 'Sent Time'] if c in df.columns), None) or pick_datetime_col(df)
    if not date_col:
        return out
    msg_col = next((c for c in df.columns if c.lower() in TEXT_HINT_COLS), None)
    chat_col = next((c for c in ['Chat', 'chat', 'Name', 'name', 'Sender', 'sender', 'From', 'Contact', 'Number', 'Address'] if c in df.columns), None)
    for _, r in df.iterrows():
        ts = parse_timestamp(str(r.get(date_col)))
        if not ts:
            continue
        text = str(r.get(msg_col, '')).strip() if msg_col else ''
        if not text:
            continue
        chat = str(r.get(chat_col, '')).strip() if chat_col else ''
        out.append({
            'mode': 'texts', 'source_file': path, 'timestamp': ts.isoformat(sep=' '), 'date_str': ts.strftime('%Y-%m-%d %H:%M'),
            'sender': chat, 'receiver': '', 'direction': '', 'chat': chat, 'subject': '',
            'message': text, 'body': text, 'attachment_count': 0, 'meta': {}
        })
    return out


def _clean_text(value):
    if value is None:
        return ''
    value = str(value).replace('\r', ' ').replace('\n', ' ').replace('\t', ' ')
    value = re.sub(r'\s+', ' ', value)
    return value.strip()


def _looks_like_phone(value):
    if not value:
        return False
    v = re.sub(r'[^\d+]', '', value)
    return bool(re.match(r'^\+?\d{7,15}$', v))


def _detect_chat_type(chat_name):
    if not chat_name:
        return 'unknown'
    if ',' in chat_name or '&' in chat_name or 'group' in chat_name.lower():
        return 'group'
    if len(chat_name.split()) >= 3 and not _looks_like_phone(chat_name):
        return 'group'
    return 'direct'


def _extract_sender_from_text(text, owner_name, chat_type, chat_name):
    text = _clean_text(text)
    if not text:
        return owner_name, '', 'Unknown', chat_name
    m = re.match(r'^(You|Me|[A-Za-z0-9_+\-() .]{2,80}?):\s+(.*)$', text, flags=re.I)
    if m:
        raw_sender = _clean_text(m.group(1))
        body = _clean_text(m.group(2))
        if raw_sender.lower() in {'you', 'me'}:
            sender = owner_name
            direction = 'Outgoing'
        else:
            sender = raw_sender
            direction = 'Incoming' if sender != owner_name else 'Outgoing'
        receiver = chat_name if chat_type == 'group' else (chat_name if direction == 'Outgoing' else owner_name)
        return sender, body, direction, receiver
    if chat_type == 'direct':
        return chat_name, text, 'Incoming', owner_name
    return 'Unknown', text, 'Unknown', chat_name


def _extract_first_media_href_from_node(node):
    if node is None:
        return ''
    a = node.find('a', href=True)
    if a and a.get('href'):
        return _clean_text(a.get('href'))
    media = node.find(['img', 'video', 'audio', 'source'], src=True)
    if media and media.get('src'):
        return _clean_text(media.get('src'))
    return ''


def _extract_media_filename_from_href(href):
    if not href:
        return ''
    clean = href.split('#', 1)[0].split('?', 1)[0].replace('/', os.sep).replace('\\', os.sep)
    return os.path.basename(clean)


def parse_whatsapp_html(path, owner_name='You'):
    out = []
    enc = detect_encoding(path)
    with open(path, 'r', encoding=enc, errors='ignore') as f:
        html = f.read()
    soup = BeautifulSoup(html, 'html.parser')
    h3 = soup.find('h3')
    chat_name = _clean_text(h3.get_text(strip=True)) if h3 else Path(path).stem
    chat_type = _detect_chat_type(chat_name)
    conversation_key = slugify(chat_name)
    seq = 0
    found_dates = soup.find_all('p', {'class': 'date'})
    if not found_dates:
        return []
    for dn in found_dates:
        ts = parse_timestamp(_clean_text(dn.get_text(' ', strip=True)))
        if not ts:
            continue
        cursor = dn.find_next_sibling()
        payloads = []
        media_href = ''
        steps = 0
        while cursor and steps < 10:
            steps += 1
            if cursor.name == 'p' and 'date' in (cursor.get('class') or []):
                break
            if not media_href:
                media_href = _extract_first_media_href_from_node(cursor)
            if cursor.name in ('p', 'table', 'div', 'span', 'li'):
                txt = _clean_text(cursor.get_text(' ', strip=True))
                if txt:
                    payloads.append(txt)
            cursor = cursor.find_next_sibling()
        text = _clean_text(' '.join(payloads))
        if not text and not media_href:
            continue
        sender, body, direction, receiver = _extract_sender_from_text(text, owner_name, chat_type, chat_name)
        media_name = _extract_media_filename_from_href(media_href)
        out.append({
            'mode': 'whatsapp', 'source_file': path, 'timestamp': ts.isoformat(sep=' '), 'date_str': ts.strftime('%Y-%m-%d %H:%M'),
            'sender': sender, 'receiver': receiver, 'direction': direction, 'chat': chat_name, 'subject': '',
            'message': body, 'body': body, 'attachment_count': 1 if media_name else 0,
            'meta': {'media_href': media_href, 'attachment_name': media_name, 'conversation_key': conversation_key, 'chat_type': chat_type, 'sequence_no': seq}
        })
        seq += 1
    return out


def _extract_pdf_text(path):
    texts = []
    if pdfplumber is not None:
        try:
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    txt = page.extract_text() or ''
                    if txt.strip():
                        texts.append(txt)
        except Exception:
            pass
    if not texts and PdfReader is not None:
        try:
            reader = PdfReader(path)
            for page in reader.pages:
                txt = page.extract_text() or ''
                if txt.strip():
                    texts.append(txt)
        except Exception:
            pass
    return '\n'.join(texts)


def _guess_chat_name_from_pdf(lines, fallback):
    for line in lines[:15]:
        low = line.lower()
        if 'whatsapp' in low:
            m = re.search(r"^(.*?)'s\s+whatsapp", line, re.I)
            if m:
                return _clean_text(m.group(1))
            continue
        if len(line) <= 80 and not re.search(r'\d{4}[/-]\d{2}[/-]\d{2}', line):
            return _clean_text(line)
    return fallback


def parse_whatsapp_pdf(path, owner_name='You'):
    text = _extract_pdf_text(path)
    if not text.strip():
        return []
    lines = [_clean_text(x) for x in text.splitlines() if _clean_text(x)]
    if 'whatsapp' not in text.lower() and not any(ATTACHMENT_NAME_PAT.search(x) for x in lines):
        return []
    chat_name = _guess_chat_name_from_pdf(lines, Path(path).stem)
    chat_type = _detect_chat_type(chat_name)
    conversation_key = slugify(chat_name)
    out = []
    seq = 0

    timestamp_indexes = []
    for i, line in enumerate(lines):
        ts = parse_timestamp(line)
        if ts:
            timestamp_indexes.append((i, ts))

    for pos, (idx, ts) in enumerate(timestamp_indexes):
        next_idx = timestamp_indexes[pos + 1][0] if pos + 1 < len(timestamp_indexes) else len(lines)
        payload_lines = [_clean_text(x) for x in lines[idx + 1:next_idx] if _clean_text(x)]
        body = _clean_text(' '.join(payload_lines))
        attach_name = ''
        if body:
            m = ATTACHMENT_NAME_PAT.search(body)
            attach_name = m.group('name') if m else ''

        sender = chat_name if chat_type == 'direct' else 'Unknown'
        direction = 'Incoming'
        receiver = owner_name if chat_type == 'direct' else chat_name

        if body:
            sender2, body2, direction2, receiver2 = _extract_sender_from_text(body, owner_name, chat_type, chat_name)
            if body2 != body or sender2 != 'Unknown':
                sender, body, direction, receiver = sender2, body2, direction2, receiver2

        if not body and not attach_name:
            continue

        out.append({
            'mode': 'whatsapp', 'source_file': path, 'timestamp': ts.isoformat(sep=' '), 'date_str': ts.strftime('%Y-%m-%d %H:%M'),
            'sender': sender, 'receiver': receiver, 'direction': direction, 'chat': chat_name, 'subject': '',
            'message': body, 'body': body, 'attachment_count': 1 if attach_name else 0,
            'meta': {'media_href': attach_name, 'attachment_name': attach_name, 'conversation_key': conversation_key, 'chat_type': chat_type, 'sequence_no': seq, 'source_format': 'pdf'}
        })
        seq += 1
    return out


def parse_email_file(path, extraction_dir):
    ext = Path(path).suffix.lower()
    if ext == '.eml':
        return _parse_eml(path, extraction_dir)
    if ext == '.msg' and MSG_SUPPORT:
        return _parse_msg(path, extraction_dir)
    if ext == '.mbox':
        return _parse_mbox(path, extraction_dir)
    return []


def _ensure_dir(d):
    Path(d).mkdir(parents=True, exist_ok=True)


def _save_attachment(payload, filename, out_dir):
    _ensure_dir(out_dir)
    safe_name = filename or 'attachment.bin'
    target = Path(out_dir) / safe_name
    stem = target.stem
    suffix = target.suffix
    idx = 1
    while target.exists():
        target = Path(out_dir) / f'{stem}_{idx}{suffix}'
        idx += 1
    with open(target, 'wb') as f:
        f.write(payload)
    return str(target)


def _extract_email_payload(msg):
    text_parts = []
    attachments = []
    if msg.is_multipart():
        for part in msg.walk():
            cdisp = (part.get('Content-Disposition') or '').lower()
            ctype = (part.get_content_type() or '').lower()
            if part.get_filename():
                payload = part.get_payload(decode=True) or b''
                attachments.append({'filename': part.get_filename(), 'payload': payload})
            elif ctype == 'text/plain' and 'attachment' not in cdisp:
                payload = part.get_payload(decode=True) or b''
                try:
                    text_parts.append(payload.decode(part.get_content_charset() or 'utf-8', errors='ignore'))
                except Exception:
                    text_parts.append(payload.decode('utf-8', errors='ignore'))
    else:
        payload = msg.get_payload(decode=True) or b''
        try:
            text_parts.append(payload.decode(msg.get_content_charset() or 'utf-8', errors='ignore'))
        except Exception:
            text_parts.append(payload.decode('utf-8', errors='ignore'))
    return _clean_text('\n'.join(text_parts)), attachments


def _email_record(path, dt, sender, to, subject, body, attachments):
    return [{
        'mode': 'emails', 'source_file': path, 'timestamp': dt.isoformat(sep=' ') if dt else '',
        'date_str': dt.strftime('%Y-%m-%d %H:%M') if dt else '', 'sender': _clean_text(sender),
        'receiver': _clean_text(to), 'direction': '', 'chat': '', 'subject': _clean_text(subject),
        'message': _clean_text(subject), 'body': _clean_text(body), 'attachment_count': len(attachments),
        'meta': {'attachments': attachments}
    }]


def _parse_eml(path, extraction_dir):
    with open(path, 'rb') as f:
        msg = message_from_binary_file(f)
    body, attachments = _extract_email_payload(msg)
    saved = []
    out_dir = os.path.join(extraction_dir, slugify(Path(path).stem))
    for a in attachments:
        sp = _save_attachment(a['payload'], a['filename'], out_dir)
        saved.append({'filename': a['filename'], 'saved_path': sp})
    dt = parse_timestamp(msg.get('Date', ''))
    return _email_record(path, dt, msg.get('From', ''), msg.get('To', ''), msg.get('Subject', ''), body, saved)


def _parse_msg(path, extraction_dir):
    msg = extract_msg.Message(path)
    body = _clean_text(msg.body or '')
    out_dir = os.path.join(extraction_dir, slugify(Path(path).stem))
    saved = []
    for att in msg.attachments:
        try:
            data = att.data
            name = att.longFilename or att.shortFilename or 'attachment.bin'
            sp = _save_attachment(data, name, out_dir)
            saved.append({'filename': name, 'saved_path': sp})
        except Exception:
            continue
    dt = parse_timestamp(str(msg.date or ''))
    return _email_record(path, dt, msg.sender or '', msg.to or '', msg.subject or '', body, saved)


def _parse_mbox(path, extraction_dir):
    out = []
    mbox = mailbox.mbox(path)
    for i, msg in enumerate(mbox):
        body, attachments = _extract_email_payload(msg)
        out_dir = os.path.join(extraction_dir, slugify(Path(path).stem), str(i))
        saved = []
        for a in attachments:
            sp = _save_attachment(a['payload'], a['filename'], out_dir)
            saved.append({'filename': a['filename'], 'saved_path': sp})
        dt = parse_timestamp(msg.get('Date', ''))
        out.extend(_email_record(path, dt, msg.get('From', ''), msg.get('To', ''), msg.get('Subject', ''), body, saved))
    return out


def extract_zip_to(zip_path, destination_dir):
    try:
        with ZipFile(zip_path, 'r') as zf:
            zf.extractall(destination_dir)
        return True, ''
    except BadZipFile:
        return False, 'invalid zip file'
    except Exception as e:
        return False, str(e)
