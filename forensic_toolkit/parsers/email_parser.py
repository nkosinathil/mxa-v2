"""Email parser for EML, MSG, MBOX, PST, and OST files with clear error reporting."""
import os
import mailbox
import email
from email import policy
from email.header import decode_header
from typing import List, Dict, Any
from .base import BaseParser
from ..categorizer import categorize_text

# Supported extensions
EMAIL_EXTS = {'.eml', '.msg', '.mbox', '.pst', '.ost'}

# Optional dependencies
try:
    import extract_msg
    MSG_OK = True
except ImportError:
    MSG_OK = False

try:
    import pypff
    PST_OK = True
except ImportError:
    PST_OK = False


def _decode_header(value):
    """Safely decode email header value."""
    if not value:
        return ''
    parts = []
    for chunk, encoding in decode_header(value):
        if isinstance(chunk, bytes):
            try:
                chunk = chunk.decode(encoding or 'utf-8', errors='ignore')
            except (LookupError, TypeError):
                chunk = chunk.decode('utf-8', errors='ignore')
        parts.append(str(chunk))
    return ''.join(parts).strip()


def _normalize_date(date_str: str) -> str:
    """Convert date string to a consistent format (or return empty)."""
    if not date_str:
        return ''
    return date_str


class EmailParser(BaseParser):
    def can_parse(self, file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        return ext in EMAIL_EXTS

    def parse(self, file_path: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        ext = os.path.splitext(file_path)[1].lower()
        log = context.get('log')
        try:
            if ext == '.eml':
                return self._parse_eml(file_path, context)
            if ext == '.mbox':
                return self._parse_mbox(file_path, context)
            if ext == '.msg':
                if MSG_OK:
                    return self._parse_msg(file_path, context)
                else:
                    if log:
                        log(f"[error] MSG parsing skipped: extract_msg not installed ({file_path})")
                    return []
            if ext in ('.pst', '.ost'):
                if PST_OK:
                    return self._parse_pst(file_path, context)
                else:
                    if log:
                        log(f"[error] PST/OST parsing skipped: pypff not installed ({file_path})")
                    return []
        except Exception as e:
            if log:
                log(f"[error] Email parser failed for {file_path}: {e}")
            return []
        return []

    def _build_record(self, source_file: str, date_str: str, sender: str, receiver: str,
                      subject: str, body: str, attachments: List[Dict[str, str]]) -> Dict[str, Any]:
        cat = categorize_text((subject or '') + ' ' + (body or ''), None)
        return {
            'mode': 'emails',
            'timestamp': date_str,
            'time': date_str,
            'date_str': date_str,
            'chat': subject or sender,
            'sender': sender,
            'receiver': receiver,
            'direction': '',
            'message': body,
            'body': body,
            'subject': subject,
            'category': cat,
            'categories': [cat],
            'attachment_name': '',
            'attachment': '',
            'source_file': source_file,
            'attachment_count': len(attachments),
            'attachments': attachments,
        }

    def _extract_attachments_from_message(self, msg) -> List[Dict[str, str]]:
        attachments = []
        for part in msg.walk():
            if part.get_content_disposition() == 'attachment':
                filename = part.get_filename()
                if not filename:
                    filename = 'attachment.bin'
                attachments.append({'filename': filename, 'saved_path': ''})
        return attachments

    def _get_body_from_message(self, msg) -> str:
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                cd = part.get_content_disposition()
                if ctype == 'text/plain' and cd != 'attachment':
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or 'utf-8'
                        return payload.decode(charset, errors='ignore')
                    except Exception:
                        continue
            # Fallback to HTML
            for part in msg.walk():
                if part.get_content_type() == 'text/html' and cd != 'attachment':
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or 'utf-8'
                        return payload.decode(charset, errors='ignore')
                    except Exception:
                        continue
            return ''
        else:
            try:
                payload = msg.get_payload(decode=True)
                charset = msg.get_content_charset() or 'utf-8'
                return payload.decode(charset, errors='ignore')
            except Exception:
                return str(msg.get_payload())

    def _parse_eml(self, file_path: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        with open(file_path, 'rb') as f:
            msg = email.message_from_binary_file(f, policy=policy.default)
        attachments = self._extract_attachments_from_message(msg)
        body = self._get_body_from_message(msg)
        return [self._build_record(
            file_path,
            _normalize_date(msg.get('Date', '')),
            _decode_header(msg.get('From', '')),
            _decode_header(msg.get('To', '')),
            _decode_header(msg.get('Subject', '')),
            body,
            attachments
        )]

    def _parse_mbox(self, file_path: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        records = []
        try:
            mbox = mailbox.mbox(file_path)
        except Exception:
            with open(file_path, 'rb') as f:
                mbox = mailbox.mbox(f)
        for msg in mbox:
            attachments = self._extract_attachments_from_message(msg)
            body = self._get_body_from_message(msg)
            records.append(self._build_record(
                file_path,
                _normalize_date(msg.get('Date', '')),
                _decode_header(msg.get('From', '')),
                _decode_header(msg.get('To', '')),
                _decode_header(msg.get('Subject', '')),
                body,
                attachments
            ))
        return records

    def _parse_msg(self, file_path: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        msg = extract_msg.Message(file_path)
        attachments = []
        for a in msg.attachments:
            name = a.longFilename or a.shortFilename or 'attachment.bin'
            attachments.append({'filename': name, 'saved_path': ''})
        body = msg.body or ''
        date_str = str(msg.date) if msg.date else ''
        sender = str(msg.sender) if msg.sender else ''
        receiver = str(msg.to) if msg.to else ''
        subject = str(msg.subject) if msg.subject else ''
        return [self._build_record(
            file_path, _normalize_date(date_str), sender, receiver, subject, body, attachments
        )]

    def _parse_pst(self, file_path: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not PST_OK:
            log = context.get('log')
            if log:
                log(f"[error] pypff not installed, cannot parse PST/OST: {file_path}")
            return []

        records = []
        log = context.get('log')
        try:
            pst = pypff.file()
            pst.open(file_path)
        except Exception as e:
            if log:
                log(f"[error] Failed to open PST/OST file {file_path}: {e}")
            return []

        def process_folder(folder):
            for message in folder.sub_messages:
                try:
                    subject = message.subject or ''
                    sender_name = message.sender_name or ''
                    sender_email = message.sender_email_address or ''
                    if sender_name and sender_email:
                        sender = f"{sender_name} <{sender_email}>"
                    else:
                        sender = sender_name or sender_email or ''

                    recipients = []
                    for recipient in message.recipients:
                        if recipient.display_name:
                            recipients.append(recipient.display_name)
                        elif recipient.email_address:
                            recipients.append(recipient.email_address)
                    receiver = ', '.join(recipients) if recipients else ''

                    date_str = ''
                    try:
                        if message.creation_time:
                            date_str = message.creation_time.isoformat()
                        elif message.client_submit_time:
                            date_str = message.client_submit_time.isoformat()
                    except Exception:
                        pass

                    body = ''
                    try:
                        if message.plain_text_body:
                            body = message.plain_text_body
                        elif message.html_body:
                            body = message.html_body
                    except Exception:
                        pass

                    attachments = []
                    try:
                        for attachment in message.attachments:
                            name = attachment.name or 'attachment.bin'
                            attachments.append({'filename': name, 'saved_path': ''})
                    except Exception:
                        pass

                    records.append(self._build_record(
                        file_path, _normalize_date(date_str), sender, receiver,
                        subject, body, attachments
                    ))
                except Exception as e:
                    if log:
                        log(f"[error] Error processing message in PST/OST {file_path}: {e}")

            for subfolder in folder.sub_folders:
                process_folder(subfolder)

        try:
            for folder in pst.root_folders:
                process_folder(folder)
        except Exception as e:
            if log:
                log(f"[error] Error traversing PST/OST folders in {file_path}: {e}")
        finally:
            pst.close()

        if log and len(records) == 0:
            log(f"[warning] No messages extracted from PST/OST: {file_path}")
        return records