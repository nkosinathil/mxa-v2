"""Parser for WhatsApp HTML exports."""
import os
import re
from typing import List, Dict, Any

from bs4 import BeautifulSoup

from .base import BaseParser
from ..utils import detect_encoding, parse_timestamp
from ..categorizer import categorize_text


PLACEHOLDER_VALUES = {"", "unknown", "you", "me", "system", "n/a", "none"}


def _clean_text(value: str) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\r", " ").replace("\n", " ").replace("\t", " ")).strip()


def _pick_bs4_parser() -> str:
    try:
        import lxml  # noqa: F401
        return "lxml"
    except Exception:
        return "html.parser"


def _extract_first_media_href_from_node(node) -> str:
    if node is None:
        return ""
    a = node.find("a", href=True)
    if a and a.get("href"):
        return _clean_text(a.get("href"))
    media = node.find(["img", "video", "audio", "source"], src=True)
    if media and media.get("src"):
        return _clean_text(media.get("src"))
    return ""


def _media_filename(href: str) -> str:
    if not href:
        return ""
    clean = href.split("#", 1)[0].split("?", 1)[0]
    return os.path.basename(clean.replace("\\", os.sep).replace("/", os.sep))


def _detect_chat_type(chat_name: str) -> str:
    chat_name = _clean_text(chat_name)
    if not chat_name:
        return "unknown"
    if "," in chat_name or "&" in chat_name or "group" in chat_name.lower():
        return "group"
    if len(chat_name.split()) >= 3 and not _looks_like_phone(chat_name):
        return "group"
    return "direct"


def _looks_like_phone(value: str) -> bool:
    if not value:
        return False
    v = re.sub(r"[^\d+]", "", value)
    return bool(re.match(r"^\+?\d{7,15}$", v))


def _clean_party(value: str) -> str:
    value = _clean_text(value)
    if value.lower() in PLACEHOLDER_VALUES:
        return ""
    return value


def _chart_parties(chat_type: str, direction: str, sender: str, receiver: str, chat_name: str, owner_name: str):
    chat_type = _clean_text(chat_type).lower()
    direction = _clean_text(direction).lower()
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


class WhatsAppHTMLParser(BaseParser):
    def can_parse(self, file_path: str) -> bool:
        low = file_path.lower()
        return low.endswith((".html", ".htm")) and "whatsapp" in low

    def parse(self, file_path: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        owner_name = _clean_text(context.get("owner_name") or "You")

        try:
            with open(file_path, "r", encoding=detect_encoding(file_path), errors="ignore") as f:
                html = f.read()
        except Exception:
            return []

        soup = BeautifulSoup(html, _pick_bs4_parser())

        h3 = soup.find("h3")
        chat_name = _clean_text(h3.get_text(" ", strip=True) if h3 else os.path.splitext(os.path.basename(file_path))[0])
        chat_type = _detect_chat_type(chat_name)

        out = []
        seq = 0

        for dn in soup.find_all("p", {"class": "date"}):
            ts_text = _clean_text(dn.get_text(" ", strip=True))
            ts = parse_timestamp(ts_text)
            if not ts:
                continue

            cursor = dn.find_next_sibling()
            payloads = []
            media_href = ""
            steps = 0

            while cursor and steps < 10:
                steps += 1
                if cursor.name == "p" and "date" in (cursor.get("class") or []):
                    break
                if not media_href:
                    media_href = _extract_first_media_href_from_node(cursor)
                txt = _clean_text(cursor.get_text(" ", strip=True)) if hasattr(cursor, "get_text") else ""
                if txt:
                    payloads.append(txt)
                cursor = cursor.find_next_sibling()

            text = _clean_text(" ".join(payloads))
            if not text and not media_href:
                continue

            sender = ""
            receiver = ""
            direction = ""
            body = text

            m = re.match(r"^(You|Me|[A-Za-z0-9_+\-() .]{2,80}?):\s+(.*)$", text, flags=re.I)
            if m:
                raw_sender = _clean_text(m.group(1))
                body = _clean_text(m.group(2))

                if raw_sender.lower() in {"you", "me"}:
                    sender = owner_name
                    direction = "Outgoing"
                    receiver = chat_name
                else:
                    sender = raw_sender
                    direction = "Incoming"
                    receiver = owner_name if chat_type == "direct" else chat_name
            else:
                body = text
                if chat_type == "direct":
                    sender = chat_name
                    direction = "Incoming"
                    receiver = owner_name
                else:
                    sender = "Unknown"
                    direction = "Unknown"
                    receiver = chat_name

            media_name = _media_filename(media_href)
            cat = categorize_text(body, context.get("category_config"))

            chart_sender, chart_receiver = _chart_parties(
                chat_type=chat_type,
                direction=direction,
                sender=sender,
                receiver=receiver,
                chat_name=chat_name,
                owner_name=owner_name,
            )

            out.append({
                "mode": "whatsapp",
                "timestamp": ts.isoformat(sep=" ", timespec="minutes"),
                "time": ts.strftime("%Y-%m-%d %H:%M"),
                "date_str": ts.strftime("%Y-%m-%d %H:%M"),
                "chat": chat_name,
                "chat_type": chat_type,
                "sender": sender,
                "receiver": receiver,
                "direction": direction,
                "chart_sender": chart_sender,
                "chart_receiver": chart_receiver,
                "message": body,
                "body": body,
                "subject": "",
                "category": cat,
                "categories": [cat],
                "conversation_key": chat_name,
                "message_id": f"{chat_name}_{seq}",
                "sequence_no": seq,
                "attachment_name": media_name,
                "attachment": media_name,
                "source_file": file_path,
                "owner_name": owner_name,
            })
            seq += 1

        return out