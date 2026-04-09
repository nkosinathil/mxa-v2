import os
import json
import html
import re
from collections import Counter, defaultdict

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp",
    ".tif", ".tiff", ".heic", ".heif"
}



def clean_text(value):
    if value is None:
        return ""
    try:
        return str(value).encode("utf-8", "replace").decode("utf-8")
    except Exception:
        try:
            return str(value)
        except Exception:
            return ""


def clean_obj(value):
    if isinstance(value, dict):
        return {clean_text(k): clean_obj(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean_obj(v) for v in value]
    if isinstance(value, tuple):
        return [clean_obj(v) for v in value]
    return clean_text(value) if isinstance(value, str) else value

def html_escape(value):
    if value is None:
        return ""
    return html.escape(clean_text(value), quote=True)


def nl2br(value):
    return html_escape(value).replace("\n", "<br>")


def safe_relpath(target_path, start_dir):
    try:
        return os.path.relpath(target_path, start_dir).replace("\\", "/")
    except Exception:
        return ""


def conversation_anchor(record):
    rid = record.get("id") or record.get("record_id") or ""
    return f"comm-{rid}" if rid else ""


def conversation_page_for_mode(mode):
    mode = (mode or "").lower()
    if mode == "whatsapp":
        return "whatsapp_threads.html"
    if mode in {"texts", "text", "sms"}:
        return "texts_threads.html"
    if mode == "calls":
        return "calls_threads.html"
    if mode in {"emails", "email"}:
        return "emails_threads.html"
    if mode == "audio":
        return "audio_threads.html"
    return "index.html"


def conversation_href(record):
    page = conversation_page_for_mode(record.get("mode"))
    anchor = conversation_anchor(record)
    return f"{page}#{anchor}" if anchor else page


def source_view_href(record, dashboard_dir):
    src = record.get("source_file") or ""
    if src and str(src).lower().endswith((".html", ".htm")) and os.path.exists(src):
        rel = safe_relpath(src, dashboard_dir)
        if rel:
            return rel
    return conversation_href(record)


def attachment_link_html(record, dashboard_dir):
    path = record.get("attachment_path") or record.get("media_path") or ""
    name = record.get("attachment_name") or record.get("attachment") or ""
    if not name:
        return ""
    if path and os.path.exists(path):
        rel = safe_relpath(path, dashboard_dir)
        if rel:
            return f"<a class='attachment-link' href='{html_escape(rel)}' target='_blank'>{html_escape(name)}</a>"
    return f"<span class='missing-attachment'>{html_escape(name)}</span>"


def month_key_from_record(record):
    raw = (record.get("timestamp") or record.get("time") or record.get("date_str") or record.get("date") or "")
    raw = str(raw).strip()
    if not raw:
        return "Unknown"
    m = re.match(r"^(\d{4})[-/](\d{2})", raw)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = re.match(r"^(\d{2})[-/](\d{2})[-/](\d{4})", raw)
    if m:
        return f"{m.group(3)}-{m.group(2)}"
    return raw[:7] if len(raw) >= 7 else "Unknown"


def dashboard_css():
    return """
body{font-family:Arial,sans-serif;margin:0;background:#f5f7fb;color:#111827}
.topbar{background:#0f172a;color:#fff;padding:16px 20px}
.topbar h1{margin:0;font-size:24px}
.topbar p{margin:6px 0 0;color:#cbd5e1}
.wrap{padding:18px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:18px}
.card{background:#fff;padding:15px;border-radius:12px;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.08);transition:.12s}
.card:hover{transform:translateY(-1px)}
.card small{display:block;color:#64748b}
.card .big{font-size:28px;font-weight:700;margin-top:6px}
.charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px;margin-bottom:18px}
.chart-card{background:#fff;border-radius:12px;padding:12px;box-shadow:0 2px 8px rgba(0,0,0,.08)}
.chart-title{font-weight:700;margin:4px 0 10px}
.chart-box{height:300px}
.tabs{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}
.tab-btn{background:#fff;border:1px solid #dbe2ea;padding:10px 14px;border-radius:999px;cursor:pointer}
.tab-btn.active{background:#0f172a;color:#fff}
.toolbar{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px}
.toolbar input,.toolbar button{padding:10px 12px;border:1px solid #dbe2ea;border-radius:10px;background:#fff}
.tab{display:none}.tab.active{display:block}
.msg-table{width:100%;border-collapse:collapse;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08)}
.msg-table th{background:#eef2f7;text-align:left;padding:10px;font-size:13px;position:sticky;top:0}
.msg-table td{padding:10px;border-bottom:1px solid #eef2f7;font-size:13px;vertical-align:top}
.attachment-link,.thread-link,.source-link{color:#1d4ed8;text-decoration:none}
.missing-attachment{color:#b91c1c}
.tag-btn,.open-inline-btn,.open-modal-btn,.ghost-btn{background:#1d4ed8;color:#fff;border:none;padding:6px 10px;border-radius:8px;cursor:pointer}
.ghost-btn{background:#475569}
.overview-card{background:#fff;border-radius:12px;padding:16px;box-shadow:0 2px 8px rgba(0,0,0,.08)}
.overview-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.network-wrap{background:#fff;border-radius:12px;padding:14px;box-shadow:0 2px 8px rgba(0,0,0,.08);margin-bottom:18px}
#networkSvg{width:100%;height:420px;background:#fff}
.inline-view{display:none;background:#fff;border:1px solid #dbe2ea;border-radius:10px;padding:10px;margin-top:8px;max-width:700px}
.inline-view img{max-width:100%;height:auto;border-radius:8px}.inline-view .note{color:#475569;font-size:12px}
.tag-modal-overlay,.viewer-modal-overlay{position:fixed;inset:0;background:rgba(15,23,42,.55);display:none;align-items:center;justify-content:center;z-index:9999}
.tag-modal{background:#fff;border-radius:14px;padding:18px;width:520px;max-width:92vw;box-shadow:0 12px 28px rgba(0,0,0,.2)}
.tag-modal textarea{width:100%;min-height:120px;margin-top:10px;padding:10px;border:1px solid #cbd5e1;border-radius:8px}
.tag-actions{margin-top:12px;display:flex;justify-content:flex-end;gap:10px;flex-wrap:wrap}
.viewer-modal{background:#fff;border-radius:14px;padding:14px;width:94vw;height:90vh;box-shadow:0 12px 28px rgba(0,0,0,.2);display:flex;flex-direction:column}
.viewer-header{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:8px;flex-wrap:wrap}
.viewer-header .meta{font-size:13px;color:#475569;max-width:70%}
.viewer-frame{width:100%;flex:1;border:1px solid #cbd5e1;border-radius:10px;background:#fff}
"""


def thread_css():
    return """
body{font-family:Arial,sans-serif;background:#eef1f7;margin:0;color:#1f2937}
.topbar{background:#0f172a;color:#fff;padding:16px 20px;display:flex;justify-content:space-between;align-items:center}
.back-link{color:#fff;text-decoration:none}
.thread-wrap{max-width:1100px;margin:20px auto;padding:0 16px}
.thread-section{background:#fff;border-radius:14px;box-shadow:0 2px 10px rgba(0,0,0,.08);padding:16px;margin-bottom:18px}
.chat-container{display:flex;flex-direction:column;gap:10px}
.chat-row{display:flex}.chat-row.incoming{justify-content:flex-start}.chat-row.outgoing{justify-content:flex-end}
.chat-bubble{max-width:70%;padding:12px 14px;border-radius:14px;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.chat-bubble.incoming{background:#fff;border:1px solid #dbe2ea}.chat-bubble.outgoing{background:#dcf8c6;border:1px solid #c9efae}
.chat-meta{font-size:12px;color:#64748b;margin-bottom:8px}.chat-text{font-size:14px;line-height:1.5;word-break:break-word}
.chat-footer{margin-top:10px;display:flex;justify-content:space-between;gap:12px;font-size:12px;align-items:center;flex-wrap:wrap}
.tag-btn,.open-modal-btn,.ghost-btn{background:#1d4ed8;color:#fff;border:none;padding:6px 10px;border-radius:8px;cursor:pointer}
.ghost-btn{background:#475569}
a{color:#1d4ed8;text-decoration:none}.missing-attachment{color:#b91c1c}.chat-row:target .chat-bubble{outline:3px solid #f59e0b}
.inline-view{display:none;background:#fff;border:1px solid #dbe2ea;border-radius:10px;padding:10px;margin-top:8px;max-width:700px}
.inline-view img{max-width:100%;height:auto;border-radius:8px}.inline-view .note{color:#475569;font-size:12px}
.tag-modal-overlay,.viewer-modal-overlay{position:fixed;inset:0;background:rgba(15,23,42,.55);display:none;align-items:center;justify-content:center;z-index:9999}
.tag-modal{background:#fff;border-radius:14px;padding:18px;width:520px;max-width:92vw;box-shadow:0 12px 28px rgba(0,0,0,.2)}
.tag-modal textarea{width:100%;min-height:120px;margin-top:10px;padding:10px;border:1px solid #cbd5e1;border-radius:8px}
.tag-actions{margin-top:12px;display:flex;justify-content:flex-end;gap:10px;flex-wrap:wrap}
.viewer-modal{background:#fff;border-radius:14px;padding:14px;width:94vw;height:90vh;box-shadow:0 12px 28px rgba(0,0,0,.2);display:flex;flex-direction:column}
.viewer-header{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:8px;flex-wrap:wrap}
.viewer-header .meta{font-size:13px;color:#475569;max-width:70%}
.viewer-frame{width:100%;flex:1;border:1px solid #cbd5e1;border-radius:10px;background:#fff}
"""


def tag_modal_html():
    return """
<div id="tagModalOverlay" class="tag-modal-overlay">
  <div class="tag-modal">
    <h3>Investigator Note / Tag</h3>
    <div id="tagTargetLabel"></div>
    <textarea id="tagText" placeholder="Add your investigator note, relevance tag, exhibit reference, or finding..."></textarea>
    <div class="tag-actions">
      <button class="ghost-btn" onclick="closeTagModal()">Cancel</button>
      <button onclick="saveTag()">Save</button>
    </div>
  </div>
</div>
"""


def viewer_modal_html():
    return """
<div id="viewerModalOverlay" class="viewer-modal-overlay">
  <div class="viewer-modal">
    <div class="viewer-header">
      <div class="meta" id="viewerModalLabel"></div>
      <div>
        <a id="viewerOpenNewTab" class="thread-link" href="#" target="_blank">Open in new tab</a>
        <button class="ghost-btn" onclick="closeViewerModal()">Close</button>
      </div>
    </div>
    <iframe id="viewerFrame" class="viewer-frame" src="about:blank"></iframe>
  </div>
</div>
"""


def common_script_js():
    return """
let currentAttachmentFoundFilter = '';
let currentOcrFilter = '';
let currentTextDetectedFilter = '';
let currentTagTarget = '';
let currentTagScope = 'record';

function showTab(id, btn){
  document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
  const el = document.getElementById(id);
  if (el) el.classList.add('active');
  document.querySelectorAll('.tab-btn').forEach(x => x.classList.remove('active'));
  if (btn) btn.classList.add('active');
}

function setAttachmentFilter(value){ currentAttachmentFoundFilter = value || ''; applyFilters(); }
function setOcrFilter(value){ currentOcrFilter = value || ''; applyFilters(); }
function setTextDetectedFilter(value){ currentTextDetectedFilter = value || ''; applyFilters(); }

function clearAllFilters(){
  currentAttachmentFoundFilter = '';
  currentOcrFilter = '';
  currentTextDetectedFilter = '';
  const sb = document.getElementById('searchBox');
  if (sb) sb.value = '';
  applyFilters();
}

function applyFilters(){
  const sb = document.getElementById('searchBox');
  const q = sb ? (sb.value || '').toLowerCase() : '';
  document.querySelectorAll('tbody.filterable-body tr').forEach(tr => {
    const search = (tr.getAttribute('data-search') || '').toLowerCase();
    const found = (tr.getAttribute('data-found') || '').toLowerCase();
    const ocr = (tr.getAttribute('data-ocr') || '').toLowerCase();
    const text = (tr.getAttribute('data-text') || '').toLowerCase();
    let ok = true;
    if (q && !search.includes(q)) ok = false;
    if (currentAttachmentFoundFilter && found !== currentAttachmentFoundFilter) ok = false;
    if (currentOcrFilter && ocr !== currentOcrFilter) ok = false;
    if (currentTextDetectedFilter && text !== currentTextDetectedFilter) ok = false;
    tr.style.display = ok ? '' : 'none';
  });
}

function storageKey(scope, targetId){ return 'mxa_investigator_tag_' + scope + '_' + targetId; }

function openTagModal(targetId, scope){
  currentTagTarget = targetId || '';
  currentTagScope = scope || 'record';
  const label = document.getElementById('tagTargetLabel');
  if (label) label.textContent = currentTagScope + ': ' + currentTagTarget;
  const existing = localStorage.getItem(storageKey(currentTagScope, currentTagTarget)) || '';
  const text = document.getElementById('tagText');
  if (text) text.value = existing;
  const overlay = document.getElementById('tagModalOverlay');
  if (overlay) overlay.style.display = 'flex';
}

function closeTagModal(){
  const overlay = document.getElementById('tagModalOverlay');
  if (overlay) overlay.style.display = 'none';
}

function saveTag(){
  if (currentTagTarget){
    const text = document.getElementById('tagText');
    localStorage.setItem(storageKey(currentTagScope, currentTagTarget), text ? (text.value || '') : '');
    renderSavedTags();
  }
  closeTagModal();
}

function renderSavedTags(){
  document.querySelectorAll('[data-investigator-target]').forEach(el => {
    const target = el.getAttribute('data-investigator-target') || '';
    const scope = el.getAttribute('data-investigator-scope') || 'record';
    const v = localStorage.getItem(storageKey(scope, target)) || '';
    el.textContent = v ? v : '';
  });
}

function exportTags(){
  const rows = [];
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (!key || !key.startsWith('mxa_investigator_tag_')) continue;
    rows.push({key: key, value: localStorage.getItem(key) || ''});
  }
  const blob = new Blob([JSON.stringify(rows, null, 2)], {type: 'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'mxa_investigator_tags.json';
  a.click();
  URL.revokeObjectURL(a.href);
}

function importTags(input){
  const file = input.files && input.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = function(){
    try {
      const data = JSON.parse(reader.result || '[]');
      (Array.isArray(data) ? data : []).forEach(item => {
        if (item && item.key && String(item.key).startsWith('mxa_investigator_tag_')) {
          localStorage.setItem(item.key, item.value || '');
        }
      });
      renderSavedTags();
      alert('Investigator tags imported.');
    } catch (e) {
      alert('Import failed: ' + e);
    }
  };
  reader.readAsText(file);
}

function openViewerModal(url, label){
  const overlay = document.getElementById('viewerModalOverlay');
  const frame = document.getElementById('viewerFrame');
  const meta = document.getElementById('viewerModalLabel');
  const openNew = document.getElementById('viewerOpenNewTab');
  if (frame) frame.src = url || 'about:blank';
  if (meta) meta.textContent = label || url || '';
  if (openNew) openNew.href = url || '#';
  if (overlay) overlay.style.display = 'flex';
}

function closeViewerModal(){
  const overlay = document.getElementById('viewerModalOverlay');
  const frame = document.getElementById('viewerFrame');
  if (frame) frame.src = 'about:blank';
  if (overlay) overlay.style.display = 'none';
}

function toggleInlinePreview(id){
  const el = document.getElementById(id);
  if (!el) return;
  el.style.display = el.style.display === 'block' ? 'none' : 'block';
}

document.addEventListener('DOMContentLoaded', function(){ renderSavedTags(); applyFilters(); });
"""


def build_cards(records, attachments, missing, by_mode):
    found_count = sum(1 for a in attachments if (a.get("found_status") == "found" or a.get("found") is True))
    ocr_done = sum(1 for a in attachments if a.get("ocr_status") == "ocr_done")
    text_detected = sum(1 for a in attachments if (a.get("text_detected") == "yes" or a.get("text_detected") is True))
    return [
        ("Total items", len(records), "overview", "clearAllFilters()"),
        ("WhatsApp", len(by_mode["whatsapp"]), "whatsapp", "clearAllFilters()"),
        ("Texts", len(by_mode["texts"]), "texts", "clearAllFilters()"),
        ("Calls", len(by_mode["calls"]), "calls", "clearAllFilters()"),
        ("Emails", len(by_mode["emails"]), "emails", "clearAllFilters()"),
        ("Audio", len(by_mode["audio"]), "audio", "clearAllFilters()"),
        ("Attachments found", found_count, "attachments", "setAttachmentFilter('found')"),
        ("Missing artifacts", len(missing), "missing", "setAttachmentFilter('missing')"),
        ("Pictures OCR processed", ocr_done, "attachments", "setOcrFilter('ocr_done')"),
        ("Images with text", text_detected, "attachments", "setTextDetectedFilter('yes')"),
    ]


def build_table_rows(data, cols, dashboard_dir):
    rows = []
    for idx, r in enumerate(data, start=1):
        mode = (r.get("mode") or "").lower()
        anchor = conversation_anchor(r)
        attachment_html = attachment_link_html(r, dashboard_dir)
        conv_href = conversation_href(r)
        source_href = source_view_href(r, dashboard_dir)
        target_id = anchor or r.get("id") or f"row-{idx}"
        investigator_note = f"<div data-investigator-target='{html_escape(target_id)}' data-investigator-scope='record' style='margin-top:6px;color:#475569;font-size:12px'></div>"

        search_blob = " ".join([
            str(r.get("sender", "")), str(r.get("receiver", "")), str(r.get("body", "")),
            str(r.get("message", "")), str(r.get("subject", "")), str(r.get("attachment", "")),
            str(r.get("attachment_name", "")), str(r.get("ocr_text", "")), str(r.get("duration", "")),
        ])
        found_status = "found" if (r.get("attachment_path") and os.path.exists(r.get("attachment_path"))) else ""
        tr_attrs = [
            f"id='{html_escape(anchor)}'" if anchor else "",
            f"data-search='{html_escape(search_blob)}'",
            f"data-mode='{html_escape(mode)}'",
            f"data-found='{html_escape(found_status)}'",
        ]
        tr_attrs = " ".join(x for x in tr_attrs if x)

        tds = [f"<td>{nl2br(r.get(key, ''))}</td>" for key, _label in cols]

        preview_html = ""
        apath = r.get("attachment_path") or ""
        aname = r.get("attachment_name") or r.get("attachment") or ""
        if apath and os.path.exists(apath):
            rel = safe_relpath(apath, dashboard_dir)
            ext = os.path.splitext(aname)[1].lower()
            preview_id = re.sub(r"[^A-Za-z0-9_-]", "_", f"pv-{idx}-{target_id}")
            if ext in IMAGE_EXTENSIONS:
                preview_html = f"<button class='open-inline-btn' onclick=\"toggleInlinePreview('{preview_id}')\">Preview</button><div class='inline-view' id='{preview_id}'><img src='{html_escape(rel)}' alt=''></div>"
            else:
                preview_html = f"<button class='open-inline-btn' onclick=\"toggleInlinePreview('{preview_id}')\">Preview</button><div class='inline-view' id='{preview_id}'><div class='note'>Preview is not embedded for this file type. Use the attachment link to open it.</div></div>"

        view_html = (
            f"<button class='open-modal-btn' onclick=\"openViewerModal('{html_escape(source_href)}','{html_escape(target_id)}')\">Open Modal</button>"
            f"<div style='margin-top:6px'><a class='thread-link' href='{html_escape(conv_href)}'>Thread Page</a></div>"
            f"<div style='margin-top:6px'><a class='source-link' href='{html_escape(source_href)}' target='_blank'>Source HTML / Source View</a></div>"
        )

        tds.append(f"<td>{attachment_html}<div style='margin-top:6px'>{preview_html}</div></td>")
        tds.append(f"<td>{view_html}</td>")
        tds.append("<td>" + f"<button class='tag-btn' onclick=\"openTagModal('{html_escape(target_id)}','record')\">Investigator Tag</button>" + investigator_note + "</td>")
        rows.append(f"<tr {tr_attrs}>{''.join(tds)}</tr>")
    return "".join(rows)


def build_table(title, tab_id, data, cols, dashboard_dir):
    headers = "".join([f"<th>{html_escape(label)}</th>" for _, label in cols])
    headers += "<th>Attachment</th><th>View</th><th>Investigator Note</th>"
    body = build_table_rows(data, cols, dashboard_dir)
    return f"""
<div id=\"{html_escape(tab_id)}\" class=\"tab\">
  <h2>{html_escape(title)}</h2>
  <table class=\"msg-table\">
    <thead><tr>{headers}</tr></thead>
    <tbody class=\"filterable-body\">{body}</tbody>
  </table>
</div>
"""


def build_attachment_rows(attachments, dashboard_dir):
    rows = []
    for idx, a in enumerate(attachments, start=1):
        name = a.get("attachment_name") or a.get("attachment") or ""
        path = a.get("attachment_path") or a.get("media_path") or ""
        found_status = a.get("found_status") or ("found" if a.get("found") else "missing")
        mode = a.get("mode") or ""
        source_file = a.get("source_file") or ""
        ocr_status = a.get("ocr_status") or ""
        text_detected = a.get("text_detected") or ""
        ocr_text = a.get("ocr_text") or ""
        reason = a.get("reason") or ""
        record_ref = {"mode": mode, "id": a.get("communication_id") or a.get("record_id") or ""}
        attachment_html = attachment_link_html({"attachment_name": name, "attachment_path": path}, dashboard_dir)
        conv_href = conversation_href(record_ref)
        source_href = safe_relpath(source_file, dashboard_dir) if source_file and os.path.exists(source_file) else conv_href
        preview_html = ""
        if path and os.path.exists(path):
            rel = safe_relpath(path, dashboard_dir)
            ext = os.path.splitext(name)[1].lower()
            preview_id = f"att_preview_{idx}"
            if ext in IMAGE_EXTENSIONS:
                preview_html = f"<button class='open-inline-btn' onclick=\"toggleInlinePreview('{preview_id}')\">Preview</button><div class='inline-view' id='{preview_id}'><img src='{html_escape(rel)}' alt=''></div>"
        search_blob = " ".join([str(mode), str(source_file), str(name), str(found_status), str(ocr_status), str(ocr_text), str(reason)])
        note_target = f"att-{idx}-{name}"
        rows.append(
            "<tr "
            f"data-search='{html_escape(search_blob)}' data-found='{html_escape(str(found_status).lower())}' "
            f"data-ocr='{html_escape(str(ocr_status).lower())}' data-text='{html_escape(str(text_detected).lower())}'>"
            f"<td>{nl2br(mode)}</td>"
            f"<td>{nl2br(source_file)}</td>"
            f"<td>{attachment_html}<div style='margin-top:6px'>{preview_html}</div></td>"
            f"<td><button class='open-modal-btn' onclick=\"openViewerModal('{html_escape(source_href)}','{html_escape(note_target)}')\">Open Modal</button><div style='margin-top:6px'><a class='thread-link' href='{html_escape(conv_href)}'>Thread Page</a></div></td>"
            f"<td>{nl2br(found_status)}</td><td>{nl2br(a.get('attachment_type') or a.get('file_ext') or '')}</td>"
            f"<td>{nl2br(ocr_status)}</td><td>{nl2br(text_detected)}</td><td>{nl2br(ocr_text)}</td><td>{nl2br(reason)}</td>"
            f"<td><button class='tag-btn' onclick=\"openTagModal('{html_escape(note_target)}','attachment')\">Investigator Tag</button><div data-investigator-target='{html_escape(note_target)}' data-investigator-scope='attachment' style='margin-top:6px;color:#475569;font-size:12px'></div></td>"
            "</tr>"
        )
    return "".join(rows)


def build_missing_rows(missing):
    rows = []
    for idx, a in enumerate(missing, start=1):
        mode = a.get("mode") or ""
        source_file = a.get("source_file") or ""
        name = a.get("attachment_name") or a.get("attachment") or ""
        reason = a.get("reason") or ""
        record_ref = {"mode": mode, "id": a.get("communication_id") or a.get("record_id") or ""}
        conv_href = conversation_href(record_ref)
        search_blob = " ".join([str(mode), str(source_file), str(name), str(reason)])
        rows.append(
            "<tr "
            f"data-search='{html_escape(search_blob)}'>"
            f"<td>{nl2br(mode)}</td><td>{nl2br(source_file)}</td><td>{nl2br(name)}</td>"
            f"<td><a class='thread-link' href='{html_escape(conv_href)}'>Thread Page</a></td>"
            f"<td>{nl2br(reason)}</td></tr>"
        )
    return "".join(rows)


def build_thread_pages(by_mode, dashboard_dir):
    page_defs = [
        ("whatsapp", "whatsapp_threads.html", "WhatsApp Conversation Viewer"),
        ("texts", "texts_threads.html", "Text Conversation Viewer"),
        ("calls", "calls_threads.html", "Call Conversation Viewer"),
        ("emails", "emails_threads.html", "Email Conversation Viewer"),
        ("audio", "audio_threads.html", "Audio Transcript Viewer"),
    ]
    for mode_key, filename, title in page_defs:
        grouped = defaultdict(list)
        for r in by_mode.get(mode_key, []):
            if mode_key == "whatsapp":
                key = r.get("chat") or r.get("sender") or "WhatsApp Conversation"
            elif mode_key == "emails":
                key = r.get("subject") or r.get("sender") or "Email Thread"
            elif mode_key == "audio":
                key = r.get("attachment_name") or r.get("subject") or "Audio File"
            else:
                left = r.get("sender") or ""
                right = r.get("receiver") or ""
                key = " / ".join([x for x in [left, right] if x]) or mode_key.title()
            grouped[key].append(r)

        sections = []
        for thread_name, items in grouped.items():
            items = sorted(items, key=lambda x: str(x.get("timestamp") or x.get("time") or x.get("date_str") or ""))
            bubbles = []
            for idx, r in enumerate(items, start=1):
                anchor = conversation_anchor(r)
                direction = (r.get("direction") or "").lower()
                bubble_class = "outgoing" if ("out" in direction or direction == "sent") else "incoming"
                body = r.get("body") or r.get("message") or r.get("subject") or ""
                meta = " | ".join([str(x) for x in [r.get("time") or r.get("date_str") or "", r.get("sender") or "", r.get("receiver") or "", r.get("duration") or ""] if x])
                attachment_html = attachment_link_html(r, dashboard_dir)
                source_href = source_view_href(r, dashboard_dir)
                tag_target = anchor or r.get("id") or f"thread-{mode_key}-{idx}"
                preview_html = ""
                apath = r.get("attachment_path") or ""
                aname = r.get("attachment_name") or r.get("attachment") or ""
                if apath and os.path.exists(apath):
                    rel = safe_relpath(apath, dashboard_dir)
                    ext = os.path.splitext(aname)[1].lower()
                    preview_id = f"thread_preview_{mode_key}_{idx}"
                    if ext in IMAGE_EXTENSIONS:
                        preview_html = f"<button class='open-inline-btn' onclick=\"toggleInlinePreview('{preview_id}')\">Preview</button><div class='inline-view' id='{preview_id}'><img src='{html_escape(rel)}' alt=''></div>"
                footer = (
                    f"<span>{attachment_html}</span>"
                    f"<span>{preview_html}</span>"
                    f"<span><button class='open-modal-btn' onclick=\"openViewerModal('{html_escape(source_href)}','{html_escape(tag_target)}')\">Open Modal</button></span>"
                    f"<span><button class='tag-btn' onclick=\"openTagModal('{html_escape(tag_target)}','record')\">Investigator Tag</button></span>"
                    f"<span><a href='{html_escape(source_href)}' target='_blank'>Source HTML / Source View</a></span>"
                    f"<span data-investigator-target='{html_escape(tag_target)}' data-investigator-scope='record' style='color:#475569'></span>"
                )
                bubbles.append(f"<div class='chat-row {bubble_class}' id='{html_escape(anchor)}'><div class='chat-bubble {bubble_class}'><div class='chat-meta'>{nl2br(meta)}</div><div class='chat-text'>{nl2br(body)}</div><div class='chat-footer'>{footer}</div></div></div>")
            sections.append(f"<section class='thread-section'><h2>{html_escape(thread_name)}</h2><div class='chat-container'>{''.join(bubbles)}</div></section>")

        page_html = f"""
<!DOCTYPE html><html><head><meta charset='utf-8'><title>{html_escape(title)}</title><style>{thread_css()}</style></head>
<body>
<header class='topbar'><h1>{html_escape(title)}</h1><a class='back-link' href='index.html'>Back to Dashboard</a></header>
<main class='thread-wrap'>{''.join(sections) if sections else '<section class="thread-section"><h2>No items found</h2></section>'}</main>
{tag_modal_html()}
{viewer_modal_html()}
<script>{common_script_js()}</script>
</body></html>
"""
        with open(os.path.join(dashboard_dir, filename), "w", encoding="utf-8", errors="replace") as f:
            f.write(page_html)


def generate_dashboard(records, attachments, missing, out_dir):
    dashboard_dir = os.path.join(out_dir, "dashboard")
    os.makedirs(dashboard_dir, exist_ok=True)

    by_mode = defaultdict(list)
    normalized_records = []
    for r in records:
        item = dict(r)
        mode = (item.get("mode") or "unknown").lower()
        if mode == "sms":
            mode = "texts"
        item["mode"] = mode
        item["time"] = item.get("time") or item.get("timestamp") or item.get("date_str") or ""
        item["body"] = item.get("body") or item.get("message") or ""
        item["attachment"] = item.get("attachment") or item.get("attachment_name") or ""
        normalized_records.append(item)
        by_mode[mode].append(item)

    cards = build_cards(normalized_records, attachments, missing, by_mode)
    cols_map = {
        "whatsapp": [("time", "Time"), ("sender", "Sender"), ("receiver", "Receiver"), ("body", "Message")],
        "texts": [("time", "Time"), ("sender", "Sender"), ("receiver", "Receiver"), ("body", "Message")],
        "calls": [("time", "Time"), ("sender", "Caller"), ("receiver", "Receiver"), ("duration", "Duration"), ("body", "Details")],
        "emails": [("time", "Time"), ("sender", "Sender"), ("receiver", "Receiver"), ("subject", "Subject"), ("body", "Body")],
        "audio": [("attachment", "Audio File"), ("duration", "Duration"), ("subject", "Title"), ("body", "Transcript / Note")],
    }

    tables_html = "".join([
        build_table("WhatsApp", "whatsapp", by_mode["whatsapp"], cols_map["whatsapp"], dashboard_dir),
        build_table("Text Messages", "texts", by_mode["texts"], cols_map["texts"], dashboard_dir),
        build_table("Calls", "calls", by_mode["calls"], cols_map["calls"], dashboard_dir),
        build_table("Emails", "emails", by_mode["emails"], cols_map["emails"], dashboard_dir),
        build_table("Audio", "audio", by_mode["audio"], cols_map["audio"], dashboard_dir),
    ])

    attachment_rows = build_attachment_rows(attachments, dashboard_dir)
    missing_rows = build_missing_rows(missing)

    monthly_counts = Counter()
    nodes_counter = Counter()
    pair_counter = Counter()
    sender_counts = Counter()
    receiver_counts = Counter()
    for r in normalized_records:
        monthly_counts[month_key_from_record(r)] += 1
        s = str(r.get("sender") or "").strip()
        t = str(r.get("receiver") or "").strip()
        if s:
            nodes_counter[s] += 1
        if t:
            nodes_counter[t] += 1
        if s and t:
            pair_counter[(s, t)] += 1
        if s and s.lower() not in {"unknown"}:
            sender_counts[s] += 1
        if t and t.lower() not in {"unknown"}:
            receiver_counts[t] += 1

    timeline_rows = [["Month", "Items"]] + [[k, monthly_counts[k]] for k in sorted(monthly_counts.keys())]
    mode_rows = [["Mode", "Count"], ["WhatsApp", len(by_mode["whatsapp"])], ["Texts", len(by_mode["texts"])], ["Calls", len(by_mode["calls"])], ["Emails", len(by_mode["emails"])], ["Audio", len(by_mode["audio"])]]
    top_sender_rows = [["Sender", "Count"]] + [[k, v] for k, v in sender_counts.most_common(10)]
    top_receiver_rows = [["Receiver", "Count"]] + [[k, v] for k, v in receiver_counts.most_common(10)]
    nodes = [{"id": name, "label": name, "value": count} for name, count in nodes_counter.most_common(18)]
    node_ids = set(x["id"] for x in nodes)
    links = [{"source": src, "target": dst, "value": count} for (src, dst), count in pair_counter.most_common(30) if src in node_ids and dst in node_ids]

    cards_html = []
    for label, value, tab_name, js_action in cards:
        js = f"showTab('{tab_name}');{js_action};applyFilters();"
        cards_html.append(f"<div class='card' onclick=\"{html_escape(js)}\"><small>{html_escape(label)}</small><div class='big'>{int(value)}</div></div>")

    overview_items = [("Total communication items", len(normalized_records)), ("WhatsApp items", len(by_mode["whatsapp"])), ("Text messages", len(by_mode["texts"])), ("Calls", len(by_mode["calls"])), ("Emails", len(by_mode["emails"])), ("Audio", len(by_mode["audio"])), ("Linked attachments", len(attachments))]
    overview_boxes = "".join(f"<div class='overview-card'><strong>{html_escape(k)}</strong><div style='font-size:28px;margin-top:6px'>{v}</div></div>" for k, v in overview_items)

    index_html = f"""
<!DOCTYPE html>
<html><head><meta charset='utf-8'><title>MxA Communication Dashboard</title><script src='https://www.gstatic.com/charts/loader.js'></script><style>{dashboard_css()}</style></head>
<body>
<header class='topbar'><h1>MxA Communication Intelligence</h1><p>Conversation review, source HTML modal view, audio transcript support, and investigator tagging.</p></header>
<div class='wrap'>
  <div class='kpis'>{''.join(cards_html)}</div>
  <div class='charts'>
    <div class='chart-card'><div class='chart-title'>Monthly Timeline</div><div id='timelineChart' class='chart-box'></div></div>
    <div class='chart-card'><div class='chart-title'>Communication by Mode</div><div id='modeChart' class='chart-box'></div></div>
    <div class='chart-card'><div class='chart-title'>Top Senders</div><div id='topSendersChart' class='chart-box'></div></div>
    <div class='chart-card'><div class='chart-title'>Top Receivers</div><div id='topReceiversChart' class='chart-box'></div></div>
  </div>
  <div class='network-wrap'><div class='chart-title'>Communication Network Graph</div><svg id='networkSvg' viewBox='0 0 1000 420'></svg></div>
  <div class='tabs'>
    <button class='tab-btn active' onclick="showTab('overview', this)">Overview</button>
    <button class='tab-btn' onclick="showTab('whatsapp', this)">WhatsApp</button>
    <button class='tab-btn' onclick="showTab('texts', this)">Text Messages</button>
    <button class='tab-btn' onclick="showTab('calls', this)">Calls</button>
    <button class='tab-btn' onclick="showTab('emails', this)">Emails</button>
    <button class='tab-btn' onclick="showTab('audio', this)">Audio</button>
    <button class='tab-btn' onclick="showTab('attachments', this)">Attachments</button>
    <button class='tab-btn' onclick="showTab('missing', this)">Missing Artifacts</button>
  </div>
  <div class='toolbar'>
    <input id='searchBox' type='text' placeholder='Search messages, email bodies, OCR text, transcript, attachment names...' onkeyup='applyFilters()'>
    <button onclick='clearAllFilters()'>Clear Filters</button>
    <button onclick='exportTags()'>Export Investigator Tags</button>
    <label class='ghost-btn' style='display:inline-flex;align-items:center;gap:8px'>Import Tags<input type='file' accept='.json,application/json' onchange='importTags(this)' style='display:none'></label>
  </div>
  <div id='overview' class='tab active'><div class='overview-grid'>{overview_boxes}</div></div>
  {tables_html}
  <div id='attachments' class='tab'><h2>Attachments</h2><table class='msg-table'><thead><tr><th>Mode</th><th>Source</th><th>Attachment</th><th>View</th><th>Status</th><th>Type</th><th>OCR Status</th><th>Text Detected</th><th>OCR Text</th><th>Reason</th><th>Investigator Note</th></tr></thead><tbody class='filterable-body'>{attachment_rows}</tbody></table></div>
  <div id='missing' class='tab'><h2>Missing Artifacts</h2><table class='msg-table'><thead><tr><th>Mode</th><th>Source</th><th>Missing Attachment</th><th>View</th><th>Reason</th></tr></thead><tbody class='filterable-body'>{missing_rows}</tbody></table></div>
</div>
{tag_modal_html()}
{viewer_modal_html()}
<script>
const timelineRows = {json.dumps(clean_obj(timeline_rows))};
const modeRows = {json.dumps(clean_obj(mode_rows))};
const topSenderRows = {json.dumps(clean_obj(top_sender_rows))};
const topReceiverRows = {json.dumps(clean_obj(top_receiver_rows))};
const networkNodes = {json.dumps(clean_obj(nodes))};
const networkLinks = {json.dumps(clean_obj(links))};
{common_script_js()}
google.charts.load('current', {{packages:['corechart']}});
google.charts.setOnLoadCallback(drawCharts);
function drawCharts(){{
  const t = google.visualization.arrayToDataTable(timelineRows.length > 1 ? timelineRows : [["Month","Items"],["None",0]]);
  new google.visualization.LineChart(document.getElementById('timelineChart')).draw(t, {{legend:{{position:'none'}}, height:300, chartArea:{{left:55, top:20, width:'80%', height:'70%'}}}});
  const m = google.visualization.arrayToDataTable(modeRows);
  const modeChart = new google.visualization.ColumnChart(document.getElementById('modeChart'));
  google.visualization.events.addListener(modeChart, 'select', function(){{ const sel=modeChart.getSelection(); if(!sel.length) return; const label=m.getValue(sel[0].row,0); if(label==='WhatsApp') showTab('whatsapp'); if(label==='Texts') showTab('texts'); if(label==='Calls') showTab('calls'); if(label==='Emails') showTab('emails'); if(label==='Audio') showTab('audio'); }});
  modeChart.draw(m, {{legend:{{position:'none'}}, height:300, chartArea:{{left:55, top:20, width:'80%', height:'70%'}}}});
  const s = google.visualization.arrayToDataTable(topSenderRows.length > 1 ? topSenderRows : [["Sender","Count"],["None",0]]);
  const sc = new google.visualization.BarChart(document.getElementById('topSendersChart'));
  google.visualization.events.addListener(sc, 'select', function(){{ const sel=sc.getSelection(); if(!sel.length) return; const label=s.getValue(sel[0].row,0); const sb=document.getElementById('searchBox'); if(sb) sb.value=label; applyFilters(); }});
  sc.draw(s, {{legend:{{position:'none'}}, height:300, chartArea:{{left:120, top:20, width:'65%', height:'70%'}}}});
  const r = google.visualization.arrayToDataTable(topReceiverRows.length > 1 ? topReceiverRows : [["Receiver","Count"],["None",0]]);
  const rc = new google.visualization.BarChart(document.getElementById('topReceiversChart'));
  google.visualization.events.addListener(rc, 'select', function(){{ const sel=rc.getSelection(); if(!sel.length) return; const label=r.getValue(sel[0].row,0); const sb=document.getElementById('searchBox'); if(sb) sb.value=label; applyFilters(); }});
  rc.draw(r, {{legend:{{position:'none'}}, height:300, chartArea:{{left:120, top:20, width:'65%', height:'70%'}}}});
}}
function drawNetworkGraph(){{
  const svg=document.getElementById('networkSvg'); if(!svg) return; svg.innerHTML=''; const width=1000, height=420, cx=width/2, cy=height/2, radius=150;
  const nodes=networkNodes.map((n,i)=>{{ const angle=(Math.PI*2*i)/Math.max(networkNodes.length,1); return {{...n, x:cx+Math.cos(angle)*radius*(1+(i%3)*0.15), y:cy+Math.sin(angle)*radius*(1+(i%3)*0.15)}}; }});
  const map={{}}; nodes.forEach(n=>map[n.id]=n);
  networkLinks.forEach(link=>{{ const s=map[link.source], t=map[link.target]; if(!s||!t) return; const line=document.createElementNS('http://www.w3.org/2000/svg','line'); line.setAttribute('x1',s.x); line.setAttribute('y1',s.y); line.setAttribute('x2',t.x); line.setAttribute('y2',t.y); line.setAttribute('stroke','#94a3b8'); line.setAttribute('stroke-width',String(Math.max(1, Math.min(6, link.value)))); line.setAttribute('opacity','0.7'); svg.appendChild(line); }});
  nodes.forEach(n=>{{ const g=document.createElementNS('http://www.w3.org/2000/svg','g'); g.style.cursor='pointer'; const circle=document.createElementNS('http://www.w3.org/2000/svg','circle'); circle.setAttribute('cx',n.x); circle.setAttribute('cy',n.y); circle.setAttribute('r',String(Math.max(12, Math.min(28, 10+n.value)))); circle.setAttribute('fill','#2563eb'); circle.setAttribute('opacity','0.9'); const text=document.createElementNS('http://www.w3.org/2000/svg','text'); text.setAttribute('x',n.x); text.setAttribute('y',n.y+4); text.setAttribute('text-anchor','middle'); text.setAttribute('fill','white'); text.setAttribute('font-size','10'); text.textContent=n.label.length>14?n.label.slice(0,14)+'…':n.label; g.appendChild(circle); g.appendChild(text); g.addEventListener('click', function(){{ const sb=document.getElementById('searchBox'); if(sb) sb.value=n.label; showTab('whatsapp'); applyFilters(); }}); svg.appendChild(g); }});
}}
window.addEventListener('resize', function(){{ if(window.google) drawCharts(); drawNetworkGraph(); }});
drawNetworkGraph();
</script>
</body></html>
"""
    with open(os.path.join(dashboard_dir, "index.html"), "w", encoding="utf-8", errors="replace") as f:
        f.write(index_html)
    build_thread_pages(by_mode, dashboard_dir)
