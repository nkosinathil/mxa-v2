import os
import sqlite3
from pathlib import Path
from typing import Iterable, List, Dict, Any, Optional
from .categorizer import clean_category_name, normalize_category_list, enforce_generic_categories


SCHEMA_VERSION = 5


class DB:
    def __init__(self, db_path):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA journal_mode=WAL;')
        self.conn.execute('PRAGMA foreign_keys=ON;')
        self._create()

    def _create(self):
        self._create_base_tables()
        self._ensure_schema_version_table()
        self._run_migrations()
        self._ensure_indexes()
        self._cleanup_invalid_categories()
        self.conn.commit()

    def _create_base_tables(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS communications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mode TEXT,
                source_file TEXT,
                timestamp TEXT,
                date_str TEXT,
                sender TEXT,
                receiver TEXT,
                direction TEXT,
                chat TEXT,
                subject TEXT,
                message TEXT,
                body TEXT,
                category TEXT DEFAULT 'All items',
                categories TEXT DEFAULT 'All items',
                transcription_status TEXT DEFAULT '',
                transcription_reason TEXT DEFAULT '',
                attachment_count INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                communication_id INTEGER,
                mode TEXT,
                source_file TEXT,
                attachment_name TEXT,
                attachment_path TEXT,
                preview_image_path TEXT DEFAULT '',
                preview_doc_path TEXT DEFAULT '',
                preview_media_path TEXT DEFAULT '',
                attachment_type TEXT,
                file_ext TEXT,
                found_status TEXT,
                width INTEGER,
                height INTEGER,
                text_detected TEXT,
                ocr_status TEXT,
                ocr_text TEXT,
                reason TEXT,
                gps_lat REAL,
                gps_lon REAL,
                gps_alt REAL,
                gps_timestamp TEXT,
                gps_source TEXT DEFAULT '',
                gps_confidence REAL,
                exif_make TEXT DEFAULT '',
                exif_model TEXT DEFAULT '',
                exif_datetime_original TEXT DEFAULT '',
                has_gps INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                color TEXT DEFAULT '#2f7de1',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS item_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                communication_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (communication_id, tag_id)
            );
            """
        )

    def _ensure_schema_version_table(self):
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        count = self.conn.execute('SELECT COUNT(*) FROM schema_version').fetchone()[0]
        if count == 0:
            self.conn.execute('INSERT INTO schema_version(version) VALUES (0)')

    def _get_schema_version(self) -> int:
        row = self.conn.execute('SELECT MAX(version) FROM schema_version').fetchone()
        return int(row[0] or 0)

    def _set_schema_version(self, version: int):
        self.conn.execute('DELETE FROM schema_version')
        self.conn.execute('INSERT INTO schema_version(version) VALUES (?)', (int(version),))

    def _table_columns(self, table_name: str) -> set[str]:
        return {row[1] for row in self.conn.execute(f"PRAGMA table_info({table_name})").fetchall()}

    def _ensure_columns(self, table_name: str, columns: dict[str, str]):
        existing = self._table_columns(table_name)
        for name, ddl_type in columns.items():
            if name not in existing:
                self.conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {name} {ddl_type}")

    def _run_migrations(self):
        current = self._get_schema_version()

        if current < 1:
            self._ensure_columns('communications', {
                'category': "TEXT DEFAULT 'All items'",
                'categories': "TEXT DEFAULT 'All items'",
                'transcription_status': "TEXT DEFAULT ''",
                'transcription_reason': "TEXT DEFAULT ''",
                'attachment_count': 'INTEGER DEFAULT 0',
            })
            self._ensure_columns('attachments', {
                'preview_image_path': "TEXT DEFAULT ''",
                'preview_doc_path': "TEXT DEFAULT ''",
                'preview_media_path': "TEXT DEFAULT ''",
            })
            current = 1
            self._set_schema_version(current)

        if current < 2:
            self._ensure_columns('attachments', {
                'gps_lat': 'REAL',
                'gps_lon': 'REAL',
                'gps_alt': 'REAL',
                'gps_timestamp': 'TEXT',
                'gps_source': "TEXT DEFAULT ''",
                'gps_confidence': 'REAL',
            })
            current = 2
            self._set_schema_version(current)

        if current < 3:
            # Reserve structured fields for safe future upgrades without breaking older cases.
            self._ensure_columns('communications', {
                'schema_notes': "TEXT DEFAULT ''",
            })
            self._ensure_columns('attachments', {
                'metadata_json': "TEXT DEFAULT ''",
            })
            current = 3
            self._set_schema_version(current)


        if current < 4:
            self._ensure_columns('attachments', {
                'exif_make': "TEXT DEFAULT ''",
                'exif_model': "TEXT DEFAULT ''",
                'exif_datetime_original': "TEXT DEFAULT ''",
                'has_gps': 'INTEGER DEFAULT 0',
            })
            current = 4
            self._set_schema_version(current)

        # Safety net so direct upgrades from much older databases still succeed even if version metadata was missing.
        self._ensure_columns('communications', {
            'category': "TEXT DEFAULT 'All items'",
            'categories': "TEXT DEFAULT 'All items'",
            'transcription_status': "TEXT DEFAULT ''",
            'transcription_reason': "TEXT DEFAULT ''",
            'attachment_count': 'INTEGER DEFAULT 0',
            'schema_notes': "TEXT DEFAULT ''",
        })
        self._ensure_columns('attachments', {
            'preview_image_path': "TEXT DEFAULT ''",
            'preview_doc_path': "TEXT DEFAULT ''",
            'preview_media_path': "TEXT DEFAULT ''",
            'gps_lat': 'REAL',
            'gps_lon': 'REAL',
            'gps_alt': 'REAL',
            'gps_timestamp': 'TEXT',
            'gps_source': "TEXT DEFAULT ''",
            'gps_confidence': 'REAL',
            'metadata_json': "TEXT DEFAULT ''",
            'exif_make': "TEXT DEFAULT ''",
            'exif_model': "TEXT DEFAULT ''",
            'exif_datetime_original': "TEXT DEFAULT ''",
            'has_gps': 'INTEGER DEFAULT 0',
        })
        self._set_schema_version(SCHEMA_VERSION)

    def _ensure_indexes(self):
        self.conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_communications_mode ON communications(mode);
            CREATE INDEX IF NOT EXISTS idx_communications_timestamp ON communications(timestamp);
            CREATE INDEX IF NOT EXISTS idx_communications_sender ON communications(sender);
            CREATE INDEX IF NOT EXISTS idx_communications_receiver ON communications(receiver);
            CREATE INDEX IF NOT EXISTS idx_communications_category ON communications(category);
            CREATE INDEX IF NOT EXISTS idx_attachments_comm_id ON attachments(communication_id);
            CREATE INDEX IF NOT EXISTS idx_attachments_gps_lat_lon ON attachments(gps_lat, gps_lon);
            CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);
            CREATE INDEX IF NOT EXISTS idx_item_tags_comm_id ON item_tags(communication_id);
            -- Additional indexes for performance
            CREATE INDEX IF NOT EXISTS idx_communications_chat ON communications(chat);
            CREATE INDEX IF NOT EXISTS idx_communications_source_file ON communications(source_file);
            """
        )

    def get_schema_info(self) -> Dict[str, Any]:
        return {
            'db_path': self.db_path,
            'schema_version': self._get_schema_version(),
            'communications_columns': sorted(self._table_columns('communications')),
            'attachments_columns': sorted(self._table_columns('attachments')),
        }


    def _normalize_comm_categories(self, row: Dict[str, Any]) -> tuple[str, str]:
        primary = clean_category_name(row.get('category') or '')
        labels = normalize_category_list(row.get('categories'), fallback=primary or 'Personal')
        labels = [c for c in labels if c.lower() != 'all items']
        labels = enforce_generic_categories(labels) or labels or ['Personal']
        if not primary or primary.lower() not in {c.lower() for c in labels}:
            primary = labels[0]
        categories_text = ', '.join(labels)
        return primary, categories_text

    def _cleanup_invalid_categories(self):
        rows = self.query("SELECT id, category, categories FROM communications")
        for row in rows:
            primary = clean_category_name(row.get('category') or '')
            labels = normalize_category_list(row.get('categories'), fallback=primary or 'Personal')
            labels = [c for c in labels if c.lower() != 'all items']
            labels = enforce_generic_categories(labels) or labels or ['Personal']
            if not primary or primary.lower() not in {c.lower() for c in labels}:
                primary = labels[0]
            categories_text = ', '.join(labels)
            if primary != (row.get('category') or '') or categories_text != (row.get('categories') or ''):
                self.conn.execute(
                    "UPDATE communications SET category = ?, categories = ? WHERE id = ?",
                    (primary, categories_text, int(row['id']))
                )
        self.conn.commit()

    def add_comm(self, row):
        primary, categories_text = self._normalize_comm_categories(row)
        cur = self.conn.execute(
            """INSERT INTO communications (
                mode, source_file, timestamp, date_str, sender, receiver,
                direction, chat, subject, message, body, category, categories, transcription_status, transcription_reason, attachment_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                row.get('mode'), row.get('source_file'), row.get('timestamp'), row.get('date_str'),
                row.get('sender'), row.get('receiver'), row.get('direction'), row.get('chat'),
                row.get('subject'), row.get('message'), row.get('body'), primary,
                categories_text,
                row.get('transcription_status', ''), row.get('transcription_reason', ''), row.get('attachment_count', 0)
            )
        )
        self.conn.commit()
        return cur.lastrowid

    def add_attachment(self, row):
        self.conn.execute(
            """INSERT INTO attachments (
                communication_id, mode, source_file, attachment_name, attachment_path,
                preview_image_path, preview_doc_path, preview_media_path,
                attachment_type, file_ext, found_status, width, height, text_detected, ocr_status,
                ocr_text, reason, gps_lat, gps_lon, gps_alt, gps_timestamp, gps_source, gps_confidence,
                exif_make, exif_model, exif_datetime_original, has_gps
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                row.get('communication_id'), row.get('mode'), row.get('source_file'),
                row.get('attachment_name'), row.get('attachment_path'),
                row.get('preview_image_path', ''), row.get('preview_doc_path', ''), row.get('preview_media_path', ''),
                row.get('attachment_type'), row.get('file_ext'), row.get('found_status'), row.get('width'), row.get('height'),
                row.get('text_detected'), row.get('ocr_status'), row.get('ocr_text'), row.get('reason'),
                row.get('gps_lat'), row.get('gps_lon'), row.get('gps_alt'), row.get('gps_timestamp'), row.get('gps_source', ''), row.get('gps_confidence'),
                row.get('exif_make', ''), row.get('exif_model', ''), row.get('exif_datetime_original', ''), 1 if row.get('gps_lat') is not None and row.get('gps_lon') is not None else int(row.get('has_gps') or 0)
            )
        )
        self.conn.commit()

    def query(self, sql, params=()):
        cur = self.conn.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def get_summary_counts(self) -> Dict[str, Dict[str, int]]:
        comms = {r['mode'] or 'Unknown': int(r['cnt']) for r in self.query(
            "SELECT COALESCE(mode, 'Unknown') AS mode, COUNT(*) AS cnt FROM communications WHERE LOWER(COALESCE(mode,'')) NOT IN ('pictures','files','photos','artifacts') GROUP BY COALESCE(mode, 'Unknown')"
        )}
        docs = {r['label']: int(r['cnt']) for r in self.query(
            """
            SELECT CASE
                WHEN LOWER(file_ext) IN ('.pdf') THEN 'PDFs'
                WHEN LOWER(file_ext) IN ('.doc', '.docx') THEN 'Word Docs'
                WHEN LOWER(file_ext) IN ('.xls', '.xlsx', '.csv') THEN 'Excel Files'
                WHEN LOWER(file_ext) IN ('.ppt', '.pptx') THEN 'Presentations'
                WHEN LOWER(file_ext) IN ('.txt') THEN 'Text Files'
                ELSE 'Other Docs'
            END AS label,
            COUNT(*) AS cnt
            FROM attachments
            WHERE LOWER(file_ext) IN ('.pdf','.doc','.docx','.xls','.xlsx','.csv','.ppt','.pptx','.txt')
            GROUP BY label
            ORDER BY cnt DESC
            """
        )}
        media = {r['label']: int(r['cnt']) for r in self.query(
            """
            SELECT CASE
                WHEN LOWER(file_ext) IN ('.jpg','.jpeg','.png','.gif','.bmp','.webp','.heic') THEN 'Images'
                WHEN LOWER(file_ext) IN ('.mp4','.mov','.avi','.mkv','.3gp','.webm') THEN 'Videos'
                WHEN LOWER(file_ext) IN ('.mp3','.wav','.aac','.m4a','.ogg','.opus','.amr') THEN 'Audio Files'
                ELSE 'Other Media'
            END AS label,
            COUNT(*) AS cnt
            FROM attachments
            WHERE LOWER(file_ext) IN (
                '.jpg','.jpeg','.png','.gif','.bmp','.webp','.heic',
                '.mp4','.mov','.avi','.mkv','.3gp','.webm',
                '.mp3','.wav','.aac','.m4a','.ogg','.opus','.amr'
            )
            GROUP BY label
            ORDER BY cnt DESC
            """
        )}
        return {'communications': comms, 'documents': docs, 'media': media}


    def get_category_breakdown(self) -> List[Dict[str, Any]]:
        return self.query(
            """
            SELECT
                CASE
                    WHEN TRIM(COALESCE(category, '')) = '' THEN 'Uncategorized'
                    WHEN LOWER(TRIM(COALESCE(category, ''))) IN ('all items', 'all categories') THEN 'Uncategorized'
                    ELSE TRIM(category)
                END AS label,
                COUNT(*) AS cnt
            FROM communications
            GROUP BY label
            ORDER BY cnt DESC, label ASC
            """
        )

    def get_top_senders(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self.query(
            """
            SELECT COALESCE(NULLIF(TRIM(sender), ''), 'Unknown') AS label, COUNT(*) AS cnt
            FROM communications
            WHERE COALESCE(NULLIF(TRIM(sender), ''), '') <> ''
            GROUP BY COALESCE(NULLIF(TRIM(sender), ''), 'Unknown')
            ORDER BY cnt DESC, label ASC
            LIMIT ?
            """,
            (int(limit),),
        )

    def get_top_receivers(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self.query(
            """
            SELECT COALESCE(NULLIF(TRIM(receiver), ''), 'Unknown') AS label, COUNT(*) AS cnt
            FROM communications
            WHERE COALESCE(NULLIF(TRIM(receiver), ''), '') <> ''
            GROUP BY COALESCE(NULLIF(TRIM(receiver), ''), 'Unknown')
            ORDER BY cnt DESC, label ASC
            LIMIT ?
            """,
            (int(limit),),
        )

    def get_transcription_summary(self) -> List[Dict[str, Any]]:
        return self.query(
            """
            SELECT
                CASE
                    WHEN LOWER(COALESCE(mode, '')) <> 'audio' THEN 'Skipped'
                    WHEN LOWER(TRIM(COALESCE(transcription_status, ''))) = 'transcribed' THEN 'Transcribed'
                    WHEN LOWER(TRIM(COALESCE(transcription_status, ''))) = 'disabled' THEN 'Disabled'
                    WHEN LOWER(TRIM(COALESCE(transcription_status, ''))) = 'skipped' THEN 'Skipped'
                    WHEN TRIM(COALESCE(body, '')) <> '' AND TRIM(COALESCE(body, '')) <> '[No transcript available]' THEN 'Transcribed'
                    WHEN LOWER(COALESCE(transcription_reason, '')) LIKE 'transcription disabled%' THEN 'Disabled'
                    ELSE 'Skipped'
                END AS label,
                COUNT(*) AS cnt
            FROM communications
            WHERE LOWER(COALESCE(mode, '')) = 'audio'
            GROUP BY label
            ORDER BY cnt DESC, label ASC
            """
        )

    def search_items(
        self,
        keyword: str = '',
        mode: str = 'All Items',
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        category: str = 'All Categories',
        tagged_only: bool = False,
        transcript_status: str = 'All Transcription States',
    ) -> List[Dict[str, Any]]:
        sql = """
        SELECT
            c.id,
            c.mode,
            c.timestamp,
            c.date_str,
            c.sender,
            c.receiver,
            c.subject,
            c.message,
            c.body,
            c.category,
            c.categories,
            c.source_file,
            c.attachment_count,
            COALESCE((SELECT a.attachment_name FROM attachments a WHERE a.communication_id = c.id LIMIT 1), '') AS attachment_name,
            COALESCE((SELECT a.attachment_path FROM attachments a WHERE a.communication_id = c.id LIMIT 1), '') AS attachment_path,
            COALESCE((SELECT GROUP_CONCAT(t.name, ', ') FROM item_tags it JOIN tags t ON t.id = it.tag_id WHERE it.communication_id = c.id), '') AS tags
        FROM communications c
        WHERE 1=1
        """
        params: List[Any] = []
        if keyword:
            sql += """
            AND (
                c.sender LIKE ? OR c.receiver LIKE ? OR c.subject LIKE ? OR c.message LIKE ? OR c.body LIKE ? OR
                EXISTS (
                    SELECT 1 FROM attachments a
                    WHERE a.communication_id = c.id AND (
                        a.attachment_name LIKE ? OR a.ocr_text LIKE ? OR a.reason LIKE ?
                    )
                )
            )
            """
            like = f"%{keyword}%"
            params.extend([like, like, like, like, like, like, like, like])
        if mode and mode.lower() not in ('all items', 'all', '*'):
            sql += " AND LOWER(COALESCE(c.mode, '')) = LOWER(?)"
            params.append(mode)
        if date_from:
            sql += " AND COALESCE(c.timestamp, c.date_str, '') >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND COALESCE(c.timestamp, c.date_str, '') <= ?"
            params.append(date_to + (' 23:59:59' if len(date_to) == 10 else ''))
        if category and category.lower() not in ('all categories', 'all'):
            if category.lower() == 'uncategorized':
                sql += " AND (TRIM(COALESCE(c.category, '')) = '' OR LOWER(TRIM(COALESCE(c.category, ''))) IN ('all items', 'all categories'))"
            else:
                sql += " AND (LOWER(COALESCE(c.category, '')) = LOWER(?) OR LOWER(COALESCE(c.categories, '')) LIKE LOWER(?))"
                params.extend([category, f'%{category}%'])
        if tagged_only:
            sql += " AND EXISTS (SELECT 1 FROM item_tags it WHERE it.communication_id = c.id)"
        if transcript_status and transcript_status.lower() not in ('all transcription states', 'all', '*'):
            sql += " AND LOWER(COALESCE(c.mode, '')) = 'audio'"
            status_value = transcript_status.lower()
            if status_value == 'transcribed':
                sql += " AND (LOWER(TRIM(COALESCE(c.transcription_status, ''))) = 'transcribed' OR (LOWER(TRIM(COALESCE(c.transcription_status, ''))) = '' AND TRIM(COALESCE(c.body, '')) <> '' AND TRIM(COALESCE(c.body, '')) <> '[No transcript available]'))"
            elif status_value == 'disabled':
                sql += " AND (LOWER(TRIM(COALESCE(c.transcription_status, ''))) = 'disabled' OR LOWER(COALESCE(c.transcription_reason, '')) LIKE 'transcription disabled%')"
            elif status_value == 'skipped':
                sql += " AND ((LOWER(TRIM(COALESCE(c.transcription_status, ''))) = 'skipped') OR (LOWER(TRIM(COALESCE(c.transcription_status, ''))) = '' AND (TRIM(COALESCE(c.body, '')) = '' OR TRIM(COALESCE(c.body, '')) = '[No transcript available]') AND LOWER(COALESCE(c.transcription_reason, '')) NOT LIKE 'transcription disabled%'))"
        sql += " ORDER BY COALESCE(c.timestamp, c.date_str, '') DESC, c.id DESC"
        return self.query(sql, params)



    def get_item_by_id(self, communication_id: int) -> Optional[Dict[str, Any]]:
        rows = self.query(
            """
            SELECT
                c.id,
                c.mode,
                c.timestamp,
                c.date_str,
                c.sender,
                c.receiver,
                c.direction,
                c.chat,
                c.subject,
                c.message,
                c.body,
                c.category,
                c.categories,
                c.transcription_status,
                c.transcription_reason,
                c.source_file,
                c.attachment_count,
                COALESCE((SELECT a.attachment_name FROM attachments a WHERE a.communication_id = c.id LIMIT 1), '') AS attachment_name,
                COALESCE((SELECT a.attachment_path FROM attachments a WHERE a.communication_id = c.id LIMIT 1), '') AS attachment_path,
                COALESCE((SELECT GROUP_CONCAT(t.name, ', ') FROM item_tags it JOIN tags t ON t.id = it.tag_id WHERE it.communication_id = c.id), '') AS tags
            FROM communications c
            WHERE c.id = ?
            """,
            (int(communication_id),),
        )
        return rows[0] if rows else None

    def get_attachments_for_item(self, communication_id: int) -> List[Dict[str, Any]]:
        return self.query(
            """
            SELECT id, attachment_name, attachment_path, attachment_type, file_ext, found_status, reason, ocr_text
            FROM attachments
            WHERE communication_id = ?
            ORDER BY id
            """,
            (int(communication_id),),
        )

    def get_thread_items(self, communication_id: int) -> List[Dict[str, Any]]:
        item = self.get_item_by_id(communication_id)
        if not item:
            return []
        mode = (item.get('mode') or '').strip()
        base_select = """
            SELECT
                c.id,
                c.mode,
                c.timestamp,
                c.date_str,
                c.sender,
                c.receiver,
                c.direction,
                c.chat,
                c.subject,
                c.message,
                c.body,
                c.category,
                c.categories,
                c.transcription_status,
                c.transcription_reason,
                c.source_file,
                COALESCE((SELECT a.attachment_name FROM attachments a WHERE a.communication_id = c.id LIMIT 1), '') AS attachment_name,
                COALESCE((SELECT a.attachment_path FROM attachments a WHERE a.communication_id = c.id LIMIT 1), '') AS attachment_path,
                COALESCE((SELECT GROUP_CONCAT(t.name, ', ') FROM item_tags it JOIN tags t ON t.id = it.tag_id WHERE it.communication_id = c.id), '') AS tags
            FROM communications c
        """
        params: List[Any] = []
        if (mode.lower() == 'whatsapp') and (item.get('chat') or '').strip():
            sql = base_select + " WHERE LOWER(COALESCE(c.mode,'')) = LOWER(?) AND COALESCE(c.chat,'') = ? ORDER BY COALESCE(c.timestamp, c.date_str, '') ASC, c.id ASC"
            params = [mode, item.get('chat')]
        elif (item.get('source_file') or '').strip():
            sql = base_select + " WHERE LOWER(COALESCE(c.mode,'')) = LOWER(?) AND COALESCE(c.source_file,'') = ? ORDER BY COALESCE(c.timestamp, c.date_str, '') ASC, c.id ASC"
            params = [mode, item.get('source_file')]
        else:
            return [item]
        rows = self.query(sql, params)
        return rows or [item]

    def get_modes(self) -> List[str]:
        rows = self.query("SELECT DISTINCT COALESCE(mode, '') AS mode FROM communications WHERE TRIM(COALESCE(mode, '')) <> '' ORDER BY mode")
        return [r['mode'] for r in rows]

    def get_categories(self) -> List[str]:
        rows = self.query("SELECT COALESCE(category, '') AS category, COALESCE(categories, '') AS categories FROM communications")
        names = set()
        for row in rows:
            primary = clean_category_name(row.get('category') or '')
            labels = normalize_category_list(row.get('categories'), fallback=primary or '')
            labels = [c for c in labels if c.lower() not in ('all items', 'generic')]
            labels = enforce_generic_categories(labels) or labels
            for name in labels:
                clean = clean_category_name(name)
                if clean:
                    names.add(clean)
            if primary and primary.lower() not in ('all items', 'generic'):
                names.add(primary)
        return sorted(names, key=lambda x: x.lower())

    def get_tags(self) -> List[Dict[str, Any]]:
        return self.query("SELECT id, name, color, created_at FROM tags ORDER BY name")

    def ensure_tag(self, name: str, color: str = '#2f7de1') -> int:
        name = (name or '').strip()
        if not name:
            raise ValueError('Tag name is required')
        self.conn.execute("INSERT OR IGNORE INTO tags(name, color) VALUES (?, ?)", (name, color))
        self.conn.commit()
        row = self.query("SELECT id FROM tags WHERE name = ?", (name,))
        return int(row[0]['id'])

    def tag_items(self, communication_ids: Iterable[int], tag_name: str, color: str = '#2f7de1'):
        tag_id = self.ensure_tag(tag_name, color=color)
        for comm_id in communication_ids:
            self.conn.execute(
                "INSERT OR IGNORE INTO item_tags(communication_id, tag_id) VALUES (?, ?)",
                (int(comm_id), tag_id),
            )
        self.conn.commit()

    def untag_items(self, communication_ids: Iterable[int], tag_name: str):
        row = self.query("SELECT id FROM tags WHERE name = ?", (tag_name,))
        if not row:
            return
        tag_id = int(row[0]['id'])
        for comm_id in communication_ids:
            self.conn.execute("DELETE FROM item_tags WHERE communication_id = ? AND tag_id = ?", (int(comm_id), tag_id))
        self.conn.commit()

    def get_tagged_items(self) -> List[Dict[str, Any]]:
        return self.search_items(tagged_only=True)

    def get_network_edges(
        self,
        mode: str = 'All Items',
        keyword: str = '',
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        category: str = 'All Categories',
    ) -> List[Dict[str, Any]]:
        sql = """
        SELECT
            COALESCE(NULLIF(TRIM(sender), ''), 'Unknown') AS source,
            COALESCE(NULLIF(TRIM(receiver), ''), 'Unknown') AS target,
            COALESCE(NULLIF(TRIM(mode), ''), 'Unknown') AS mode,
            COUNT(*) AS weight,
            MAX(COALESCE(timestamp, date_str, '')) AS last_seen
        FROM communications
        WHERE COALESCE(NULLIF(TRIM(sender), ''), '') <> ''
          AND COALESCE(NULLIF(TRIM(receiver), ''), '') <> ''
        """
        params: List[Any] = []
        if mode and mode.lower() not in ('all items', 'all', '*'):
            sql += " AND LOWER(COALESCE(mode, '')) = LOWER(?)"
            params.append(mode)
        if keyword:
            like = f"%{keyword}%"
            sql += """
            AND (
                sender LIKE ? OR receiver LIKE ? OR subject LIKE ? OR message LIKE ? OR body LIKE ? OR
                source_file LIKE ? OR chat LIKE ?
            )
            """
            params.extend([like, like, like, like, like, like, like])
        if date_from:
            sql += " AND COALESCE(timestamp, date_str, '') >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND COALESCE(timestamp, date_str, '') <= ?"
            params.append(date_to + (' 23:59:59' if len(date_to) == 10 else ''))
        if category and category.lower() not in ('all categories', 'all'):
            if category.lower() == 'uncategorized':
                sql += " AND (TRIM(COALESCE(category, '')) = '' OR LOWER(TRIM(COALESCE(category, ''))) IN ('all items', 'all categories'))"
            else:
                sql += " AND (LOWER(COALESCE(category, '')) = LOWER(?) OR LOWER(COALESCE(categories, '')) LIKE LOWER(?))"
                params.extend([category, f'%{category}%'])
        sql += " GROUP BY source, target, mode ORDER BY weight DESC, source, target"
        return self.query(sql, params)


    def get_geotagged_attachments(self) -> List[Dict[str, Any]]:
        sql = """
        SELECT
            a.id,
            a.communication_id,
            a.mode,
            a.source_file,
            a.attachment_name,
            a.attachment_path,
            a.preview_image_path,
            a.preview_doc_path,
            a.preview_media_path,
            a.attachment_type,
            a.file_ext,
            a.gps_lat,
            a.gps_lon,
            a.gps_alt,
            a.gps_timestamp,
            a.gps_source,
            a.gps_confidence,
            c.timestamp,
            c.date_str,
            c.sender,
            c.receiver,
            c.chat,
            c.message,
            c.body
        FROM attachments a
        LEFT JOIN communications c ON c.id = a.communication_id
        WHERE a.gps_lat IS NOT NULL AND a.gps_lon IS NOT NULL
          AND LOWER(COALESCE(a.file_ext, '')) IN ('.jpg','.jpeg','.png','.webp','.heic','.bmp','.gif','.tif','.tiff')
        ORDER BY COALESCE(c.timestamp, c.date_str, '')
        """
        return self.query(sql)

    def get_geo_summary(self) -> Dict[str, int]:
        image_exts = ('.jpg','.jpeg','.png','.webp','.heic','.bmp','.gif','.tif','.tiff')
        placeholders = ','.join(['?'] * len(image_exts))
        total_images = self.conn.execute(
            f"SELECT COUNT(*) FROM attachments WHERE LOWER(COALESCE(file_ext, '')) IN ({placeholders})",
            image_exts,
        ).fetchone()[0] or 0
        with_gps = self.conn.execute(
            f"SELECT COUNT(*) FROM attachments WHERE LOWER(COALESCE(file_ext, '')) IN ({placeholders}) AND gps_lat IS NOT NULL AND gps_lon IS NOT NULL",
            image_exts,
        ).fetchone()[0] or 0
        without_gps = max(int(total_images) - int(with_gps), 0)
        missing_original = self.conn.execute(
            f"SELECT COUNT(*) FROM attachments WHERE LOWER(COALESCE(file_ext, '')) IN ({placeholders}) AND TRIM(COALESCE(attachment_path, '')) = ''",
            image_exts,
        ).fetchone()[0] or 0
        return {
            'total_images': int(total_images),
            'with_gps': int(with_gps),
            'without_gps': int(without_gps),
            'missing_original': int(missing_original),
        }


    def _resolve_case_path(self, path_value: str) -> str:
        import os
        value = str(path_value or '').strip()
        if not value:
            return ''
        p = Path(value)
        if p.is_absolute() and p.exists():
            return str(p)
        case_dir = Path(self.db_path).resolve().parent
        cand = case_dir / value
        if cand.exists():
            return str(cand)
        media_cand = case_dir / 'media' / os.path.basename(value)
        if media_cand.exists():
            return str(media_cand)
        return ''

    def backfill_image_metadata(self, progress_cb=None, log_path: str = '') -> int:
        from .utils import extract_image_exif_metadata
        rows = self.query(
            """
            SELECT id, source_file, attachment_path, attachment_name, file_ext, gps_lat, gps_lon, exif_make, exif_model, exif_datetime_original
            FROM attachments
            WHERE LOWER(COALESCE(file_ext,'')) IN ('.jpg','.jpeg','.png','.bmp','.gif','.webp','.tif','.tiff','.heic','.heif')
            """
        )
        updated = 0
        log_fh = None
        if log_path:
            try:
                Path(log_path).parent.mkdir(parents=True, exist_ok=True)
                log_fh = open(log_path, 'w', encoding='utf-8')
                log_fh.write('id\tresolved_path\tstatus\thas_gps\tgps_lat\tgps_lon\texif_make\texif_model\texif_datetime_original\n')
            except Exception:
                log_fh = None
        try:
            for row in rows:
                needs = any([
                    row.get('gps_lat') is None or row.get('gps_lon') is None,
                    not str(row.get('exif_make') or '').strip(),
                    not str(row.get('exif_model') or '').strip(),
                    not str(row.get('exif_datetime_original') or '').strip(),
                ])
                if not needs:
                    if log_fh:
                        log_fh.write(
                            f"{row.get('id')}\t\talready_present\t{int(bool(row.get('gps_lat') is not None and row.get('gps_lon') is not None))}\t{row.get('gps_lat') or ''}\t{row.get('gps_lon') or ''}\t{row.get('exif_make') or ''}\t{row.get('exif_model') or ''}\t{row.get('exif_datetime_original') or ''}\n"
                        )
                    continue
                resolved = self._resolve_case_path(row.get('source_file') or '') or self._resolve_case_path(row.get('attachment_path') or row.get('attachment_name') or '')
                if not resolved:
                    if log_fh:
                        log_fh.write(f"{row.get('id')}\t\tmissing_path\t0\t\t\t\t\t\n")
                    continue
                try:
                    exif = extract_image_exif_metadata(str(resolved))
                except Exception:
                    if log_fh:
                        log_fh.write(f"{row.get('id')}\t{resolved}\texif_error\t0\t\t\t\t\t\n")
                    continue
                self.conn.execute(
                    """
                    UPDATE attachments
                    SET gps_lat=?, gps_lon=?, gps_alt=COALESCE(gps_alt, ?), gps_timestamp=COALESCE(NULLIF(gps_timestamp,''), ?),
                        gps_source=CASE WHEN gps_source='' OR gps_source IS NULL THEN 'exif' ELSE gps_source END,
                        gps_confidence=COALESCE(gps_confidence, ?),
                        exif_make=COALESCE(NULLIF(exif_make,''), ?),
                        exif_model=COALESCE(NULLIF(exif_model,''), ?),
                        exif_datetime_original=COALESCE(NULLIF(exif_datetime_original,''), ?),
                        has_gps=?
                    WHERE id=?
                    """,
                    (
                        exif.get('gps_lat'), exif.get('gps_lon'), exif.get('gps_alt'),
                        exif.get('gps_timestamp') or exif.get('exif_datetime_original') or '',
                        1.0 if exif.get('gps_lat') is not None and exif.get('gps_lon') is not None else None,
                        exif.get('exif_make') or '', exif.get('exif_model') or '', exif.get('exif_datetime_original') or '',
                        1 if exif.get('gps_lat') is not None and exif.get('gps_lon') is not None else 0,
                        row['id']
                    )
                )
                if log_fh:
                    log_fh.write(
                        f"{row.get('id')}\t{resolved}\tupdated\t{1 if exif.get('gps_lat') is not None and exif.get('gps_lon') is not None else 0}\t{exif.get('gps_lat') or ''}\t{exif.get('gps_lon') or ''}\t{exif.get('exif_make') or ''}\t{exif.get('exif_model') or ''}\t{exif.get('exif_datetime_original') or ''}\n"
                    )
                updated += 1
                if callable(progress_cb) and updated % 25 == 0:
                    progress_cb(f'[progress] Image metadata backfill updated: {updated}')
        finally:
            if log_fh:
                log_fh.close()
        if updated:
            self.conn.commit()
        return updated

    def close(self):
        self.conn.commit()
        self.conn.close()