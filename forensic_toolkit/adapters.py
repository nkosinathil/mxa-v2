import os
from pathlib import Path
from typing import Any, Dict, List


PLACEHOLDER_VALUES = {"", "unknown", "you", "me", "system", "n/a", "none"}


def _rel_to_case_output(source_file: str, saved_path: str) -> str:
    raw = _safe_str(saved_path)
    if not raw:
        return ''
    try:
        p = Path(raw)
        if not p.is_absolute():
            return raw.replace('\\', '/')
        src = Path(_safe_str(source_file))
        case_dir = src.parent if src.suffix else src
        for base in [case_dir, case_dir.parent, case_dir.parent.parent]:
            try:
                rel = p.resolve().relative_to(base.resolve())
                return str(rel).replace('\\', '/')
            except Exception:
                continue
    except Exception:
        pass
    return raw

def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _record_id(mode: str, source_file: str, timestamp: str, sender: str, receiver: str, body: str, attachment_name: str) -> str:
    payload = "||".join([
        _safe_str(mode),
        _safe_str(source_file),
        _safe_str(timestamp),
        _safe_str(sender),
        _safe_str(receiver),
        _safe_str(body),
        _safe_str(attachment_name),
    ])
    return hashlib.sha256(payload.encode("utf-8", errors="ignore")).hexdigest()[:32]


def _is_placeholder(value: str) -> bool:
    return _safe_str(value).lower() in PLACEHOLDER_VALUES


def _clean_party(value: str) -> str:
    value = _safe_str(value)
    if _is_placeholder(value):
        return ""
    return value




def _normalise_categories(value: Any, fallback: str = "All items") -> List[str]:
    if isinstance(value, (list, tuple, set)):
        items = [_safe_str(v) for v in value if _safe_str(v)]
    else:
        raw = _safe_str(value)
        items = [_safe_str(v) for v in raw.split(',') if _safe_str(v)] if raw else []
    if not items:
        items = [fallback]
    seen = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def _primary_category(row: Dict[str, Any], fallback: str = "All items") -> str:
    primary = _safe_str(row.get("category"))
    if primary:
        return primary
    cats = _normalise_categories(row.get("categories"), fallback=fallback)
    for cat in cats:
        if cat.lower() != 'all items':
            return cat
    return cats[0] if cats else fallback


def _chart_parties(chat_type: str, direction: str, sender: str, receiver: str, chat_name: str, owner_name: str):
    chat_type = _safe_str(chat_type).lower()
    direction = _safe_str(direction).lower()
    sender = _clean_party(sender)
    receiver = _clean_party(receiver)
    chat_name = _clean_party(chat_name)
    owner_name = _clean_party(owner_name)

    if chat_type == "group":
        chart_sender = sender if sender and sender.lower() != owner_name.lower() else ""
        chart_receiver = ""
        return chart_sender, chart_receiver

    if direction == "outgoing":
        return owner_name, chat_name
    if direction == "incoming":
        return chat_name, owner_name

    return sender, receiver


def normalize_whatsapp_html_row(row: Dict[str, Any]) -> Dict[str, Any]:
    timestamp = row.get("timestamp")
    date_str = row.get("date_str") or (timestamp.strftime("%Y-%m-%d %H:%M") if hasattr(timestamp, "strftime") else _safe_str(timestamp))
    body = _safe_str(row.get("message"))
    attachment_name = _safe_str(row.get("media_name") or row.get("attachment_name") or row.get("attachment") or "")
    source_file = _safe_str(row.get("source") or row.get("source_file") or row.get("source_path"))
    owner_name = _safe_str(row.get("owner_name") or row.get("owner") or "You")

    sender = _safe_str(row.get("sender"))
    receiver = _safe_str(row.get("receiver"))
    direction = _safe_str(row.get("direction"))
    chat_name = _safe_str(row.get("chat"))
    chat_type = _safe_str(row.get("chat_type") or "")

    chart_sender, chart_receiver = _chart_parties(
        chat_type=chat_type,
        direction=direction,
        sender=sender,
        receiver=receiver,
        chat_name=chat_name,
        owner_name=owner_name,
    )

    return {
        "id": _record_id("whatsapp", source_file, date_str, sender, receiver, body, attachment_name),
        "mode": "whatsapp",
        "timestamp": _safe_str(timestamp.isoformat() if hasattr(timestamp, "isoformat") else timestamp),
        "time": date_str,
        "date_str": date_str,
        "chat": chat_name,
        "sender": sender,
        "receiver": receiver,
        "direction": direction,
        "chart_sender": chart_sender,
        "chart_receiver": chart_receiver,
        "message": body,
        "body": body,
        "subject": "",
        "category": _primary_category(row, "Other / Unclassified"),
        "categories": _normalise_categories(row.get("categories") or row.get("category"), fallback="Other / Unclassified"),
        "risk_pct": row.get("risk_pct") or 0,
        "risk_level": _safe_str(row.get("risk_level") or "Low"),
        "risk_factors_json": _safe_str(row.get("risk_factors_json") or "[]"),
        "meter_numbers": _safe_str(row.get("meter_numbers") or ""),
        "meter_types": _safe_str(row.get("meter_types") or ""),
        "conversation_key": _safe_str(row.get("conversation_key") or row.get("chat")),
        "chat_type": chat_type,
        "message_id": _safe_str(row.get("message_id") or ""),
        "sequence_no": row.get("sequence_no") or 0,
        "attachment_name": attachment_name,
        "attachment": attachment_name,
        "attachment_path": "",
        "media_path": "",
        "media_exists": False,
        "media_deleted": False,
        "message_kind": _safe_str(row.get("message_kind") or ""),
        "ocr_text": "",
        "source_file": source_file,
        "source_path": source_file,
    }


def normalize_whatsapp_pdf_row(row: Dict[str, Any]) -> Dict[str, Any]:
    date_str = _safe_str(row.get("date_str") or row.get("timestamp"))
    body = _safe_str(row.get("text") or row.get("message") or "")
    attachment_name = _safe_str(row.get("media_name") or "")
    source_file = _safe_str(row.get("source_file") or row.get("source_path"))
    owner_name = _safe_str(row.get("owner_name") or row.get("owner") or "You")

    sender = _safe_str(row.get("sender"))
    receiver = _safe_str(row.get("receiver"))
    direction = _safe_str(row.get("direction"))
    chat_name = _safe_str(row.get("chat_name") or "")
    chat_type = _safe_str(row.get("chat_type") or "")

    chart_sender, chart_receiver = _chart_parties(
        chat_type=chat_type,
        direction=direction,
        sender=sender,
        receiver=receiver,
        chat_name=chat_name,
        owner_name=owner_name,
    )

    return {
        "id": _record_id("whatsapp", source_file, date_str, sender, receiver, body, attachment_name),
        "mode": "whatsapp",
        "timestamp": _safe_str(row.get("timestamp")),
        "time": date_str,
        "date_str": date_str,
        "chat": chat_name,
        "sender": sender,
        "receiver": receiver,
        "direction": direction,
        "chart_sender": chart_sender,
        "chart_receiver": chart_receiver,
        "message": body,
        "body": body,
        "subject": "",
        "category": _primary_category(row, "Other / Unclassified"),
        "categories": _normalise_categories(row.get("categories") or row.get("category"), fallback="Other / Unclassified"),
        "risk_pct": row.get("risk_pct") or 0,
        "risk_level": _safe_str(row.get("risk_level") or "Low"),
        "risk_factors_json": _safe_str(row.get("risk_factors_json") or "[]"),
        "meter_numbers": _safe_str(row.get("meter_numbers") or ""),
        "meter_types": _safe_str(row.get("meter_types") or ""),
        "conversation_key": _safe_str(row.get("conversation_key") or row.get("chat_name") or ""),
        "chat_type": chat_type,
        "message_id": "",
        "sequence_no": row.get("sequence_no") or 0,
        "attachment_name": attachment_name,
        "attachment": attachment_name,
        "attachment_path": "",
        "media_path": "",
        "media_exists": bool(row.get("media_exists")),
        "media_deleted": bool(row.get("media_deleted")),
        "message_kind": _safe_str(row.get("message_kind") or ""),
        "ocr_text": "",
        "source_file": source_file,
        "source_path": _safe_str(row.get("source_path") or source_file),
    }


def normalize_messages_row(row: Dict[str, Any]) -> Dict[str, Any]:
    date_str = _safe_str(row.get("date_str"))
    body = _safe_str(row.get("message"))
    chat = _safe_str(row.get("chat"))
    sender = _safe_str(row.get("sender") or chat)
    receiver = _safe_str(row.get("receiver") or "")
    direction = _safe_str(row.get("direction") or "")
    source_file = _safe_str(row.get("source") or row.get("source_file") or row.get("source_path"))

    return {
        "id": _record_id("texts", source_file, date_str, sender, receiver, body, ""),
        "mode": "texts",
        "timestamp": date_str,
        "time": date_str,
        "date_str": date_str,
        "chat": chat,
        "sender": sender,
        "receiver": receiver,
        "direction": direction,
        "chart_sender": _clean_party(sender),
        "chart_receiver": _clean_party(receiver),
        "message": body,
        "body": body,
        "subject": "",
        "category": _primary_category(row, "Other / Unclassified"),
        "categories": _normalise_categories(row.get("categories") or row.get("category"), fallback="Other / Unclassified"),
        "risk_pct": row.get("risk_pct") or 0,
        "risk_level": _safe_str(row.get("risk_level") or "Low"),
        "risk_factors_json": _safe_str(row.get("risk_factors_json") or "[]"),
        "meter_numbers": _safe_str(row.get("meter_numbers") or ""),
        "meter_types": _safe_str(row.get("meter_types") or ""),
        "conversation_key": chat,
        "chat_type": "",
        "message_id": "",
        "sequence_no": 0,
        "attachment_name": "",
        "attachment": "",
        "attachment_path": "",
        "media_path": "",
        "media_exists": False,
        "media_deleted": False,
        "message_kind": "",
        "ocr_text": "",
        "source_file": source_file,
        "source_path": source_file,
    }


def normalize_calls_row(row: Dict[str, Any]) -> Dict[str, Any]:
    date_str = _safe_str(row.get("date_str") or row.get("timestamp"))
    sender = _safe_str(row.get("sender") or row.get("name"))
    receiver = _safe_str(row.get("receiver") or row.get("number"))
    body = _safe_str(row.get("message") or row.get("details") or "")
    source_file = _safe_str(row.get("source") or row.get("source_file") or row.get("source_path"))

    return {
        "id": _record_id("calls", source_file, date_str, sender, receiver, body, ""),
        "mode": "calls",
        "timestamp": date_str,
        "time": date_str,
        "date_str": date_str,
        "chat": _safe_str(row.get("chat") or sender or receiver),
        "sender": sender,
        "receiver": receiver,
        "direction": _safe_str(row.get("direction") or row.get("type") or ""),
        "chart_sender": _clean_party(sender),
        "chart_receiver": _clean_party(receiver),
        "message": body,
        "body": body,
        "duration": _safe_str(row.get("duration") or ""),
        "subject": "",
        "category": _primary_category(row, "All items"),
        "categories": _normalise_categories(row.get("categories") or row.get("category"), fallback="All items"),
        "risk_pct": 0,
        "risk_level": "Low",
        "risk_factors_json": "[]",
        "meter_numbers": "",
        "meter_types": "",
        "conversation_key": _safe_str(row.get("chat") or sender or receiver),
        "chat_type": "",
        "message_id": "",
        "sequence_no": 0,
        "attachment_name": "",
        "attachment": "",
        "attachment_path": "",
        "media_path": "",
        "media_exists": False,
        "media_deleted": False,
        "message_kind": "",
        "ocr_text": "",
        "source_file": source_file,
        "source_path": source_file,
    }


def normalize_email_row(row: Dict[str, Any]) -> Dict[str, Any]:
    date_str = _safe_str(row.get("date_str") or row.get("date"))
    sender = _safe_str(row.get("from_address") or row.get("sender") or row.get("from"))
    receiver = _safe_str(row.get("to") or row.get("receiver"))
    subject = _safe_str(row.get("subject"))
    body = _safe_str(row.get("body"))
    source_file = _safe_str(row.get("source_file") or "")

    return {
        "id": _record_id("emails", source_file, date_str, sender, receiver, body, ""),
        "mode": "emails",
        "timestamp": date_str,
        "time": date_str,
        "date_str": date_str,
        "chat": subject,
        "sender": sender,
        "receiver": receiver,
        "direction": "",
        "chart_sender": _clean_party(sender),
        "chart_receiver": _clean_party(receiver),
        "message": body,
        "body": body,
        "subject": subject,
        "category": "All items",
        "categories": ["All items"],
        "risk_pct": 0,
        "risk_level": "Low",
        "risk_factors_json": "[]",
        "meter_numbers": "",
        "meter_types": "",
        "conversation_key": subject or sender,
        "chat_type": "",
        "message_id": _safe_str(row.get("message_id") or ""),
        "sequence_no": 0,
        "attachment_name": "",
        "attachment": "",
        "attachment_path": "",
        "media_path": "",
        "media_exists": False,
        "media_deleted": False,
        "message_kind": "",
        "ocr_text": "",
        "source_file": source_file,
        "source_path": source_file,
        "attachment_count": row.get("attachment_count") or 0,
        "attachments": row.get("attachments") or [],
    }


def normalize_email_attachments(email_row: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    comm_id = _safe_str(email_row.get("id"))
    for idx, att in enumerate(email_row.get("attachments") or [], start=1):
        name = _safe_str(att.get("filename") or f"attachment_{idx}")
        saved_path = _safe_str(att.get("saved_path") or "")
        stored_path = _rel_to_case_output(email_row.get("source_file"), saved_path)
        out.append({
            "id": hashlib.sha256(f"{comm_id}||{name}||{saved_path}".encode("utf-8")).hexdigest()[:32],
            "communication_id": comm_id,
            "mode": "emails",
            "source_file": _safe_str(email_row.get("source_file")),
            "attachment_name": name,
            "attachment": name,
            "attachment_path": stored_path,
            "media_path": stored_path,
            "found_status": "found" if saved_path and os.path.exists(saved_path) else "missing",
            "attachment_type": _safe_str(att.get("content_type") or ""),
            "file_ext": os.path.splitext(name)[1].lower(),
            "ocr_status": "",
            "ocr_text": "",
            "text_detected": "no",
            "reason": "" if saved_path and os.path.exists(saved_path) else "Attachment not found",
            "width": None,
            "height": None,
        })
    return out