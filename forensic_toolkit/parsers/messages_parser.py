"""Parser for Samsung/Android text message CSV/XLS/XLSX exports."""
import os
import re
from typing import List, Dict, Any
from .dataframe_parser import DataFrameParser
from ..utils import parse_timestamp, pick_datetime_col
from ..categorizer import categorize_text

TEXT_HINT_COLS = {"message", "content", "body", "text", "sms", "mms", "snippet", "subject"}


def _clean(v):
    if v is None:
        return ''
    s = str(v).replace("\u200e", " ").replace("\t", " ").replace('\\"', '"')
    s = re.sub(r'^\s*["\']+', '', s)
    s = re.sub(r'["\']+\s*$', '', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()


def _phoneish(v: str) -> str:
    s = _clean(v)
    if not s:
        return ''
    if s.lower() in {'me', 'you'}:
        return s
    out = re.sub(r'[^\d+]', '', s)
    return out or s


class MessagesParser(DataFrameParser):
    def can_parse(self, file_path: str) -> bool:
        low = file_path.lower()
        base = os.path.basename(low)
        return low.endswith((".csv", ".tsv", ".xlsx", ".xls")) and any(k in base for k in ["message", "messages", "sms", "mms"])

    def parse_dataframe(self, path_hint: str, df, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        log = context.get('log')
        owner_name = context.get('owner_name') or 'Me'

        colmap = {str(c).strip(): c for c in df.columns}
        date_col = next((colmap[c] for c in ["Date", "date", "Created", "Timestamp", "Time", "Message Date/Time", "Sent Time"] if c in colmap), None)
        if not date_col:
            date_col = pick_datetime_col(df)
        if not date_col:
            if log:
                log(f"No datetime column in {os.path.basename(path_hint)}")
            return out

        msg_col = next((c for c in df.columns if str(c).strip().lower() in TEXT_HINT_COLS), None)
        if not msg_col:
            obj_cols = [c for c in df.columns if df[c].dtype == object]
            if obj_cols:
                msg_col = max(obj_cols, key=lambda c: df[c].astype(str).str.len().fillna(0).mean())
        if not msg_col:
            return out

        number_col = next((colmap[c] for c in ["Number", "number", "Address", "address", "Phone", "phone"] if c in colmap), None)
        name_col = next((colmap[c] for c in ["Name", "name", "Contact", "contact"] if c in colmap), None)
        state_col = next((colmap[c] for c in ["SmsState", "smsstate", "State"] if c in colmap), None)
        type_col = next((colmap[c] for c in ["SmsType", "smstype", "Type", "type", "Direction", "direction"] if c in colmap), None)
        thread_col = next((colmap[c] for c in ["ThreadId", "threadid", "Thread", "thread"] if c in colmap), None)

        for _, r in df.iterrows():
            ts = parse_timestamp(str(r.get(date_col)))
            if not ts:
                continue
            text = _clean(r.get(msg_col, ""))
            if not text:
                continue

            number = _phoneish(r.get(number_col, "")) if number_col else ''
            name = _clean(r.get(name_col, "")) if name_col else ''
            sms_state = _clean(r.get(state_col, "")) if state_col else ''
            sms_type = _clean(r.get(type_col, "")) if type_col else ''
            thread_id = _clean(r.get(thread_col, "")) if thread_col else ''

            state_low = sms_state.lower()
            type_low = sms_type.lower()
            if state_low in {'sent', 'outbox', 'sending', 'queued'} or type_low in {'sent', 'outgoing'}:
                direction = 'Outgoing'
            elif state_low in {'inbox', 'received'} or type_low in {'inbox', 'incoming', 'received'}:
                direction = 'Incoming'
            else:
                direction = ''

            counterpart = number or name
            if direction == 'Outgoing':
                sender = owner_name
                receiver = counterpart
            elif direction == 'Incoming':
                sender = counterpart
                receiver = owner_name
            else:
                if name.lower() in {'me', owner_name.lower()}:
                    sender = owner_name
                    receiver = counterpart
                    direction = 'Outgoing'
                else:
                    sender = counterpart
                    receiver = owner_name if counterpart else ''
                    direction = 'Incoming' if counterpart else ''

            chat = counterpart or thread_id or owner_name
            cat = categorize_text(text, context.get('category_config'))
            out.append({
                'mode': 'texts',
                'timestamp': ts.isoformat(sep=' ', timespec='minutes'),
                'time': ts.strftime('%Y-%m-%d %H:%M'),
                'date_str': ts.strftime('%Y-%m-%d %H:%M'),
                'chat': chat,
                'sender': sender,
                'receiver': receiver,
                'direction': direction,
                'message': text,
                'body': text,
                'subject': '',
                'category': cat,
                'categories': [cat],
                'thread_id': thread_id,
                'attachment_name': '',
                'attachment': '',
                'source_file': path_hint,
            })
        if log:
            log(f"Parsed {len(out)} text messages from {os.path.basename(path_hint)}")
        return out
