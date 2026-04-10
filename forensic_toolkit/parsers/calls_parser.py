"""Parser for call log CSV/XLS/XLSX exports."""
import os
from typing import List, Dict, Any
from .dataframe_parser import DataFrameParser
from ..utils import parse_timestamp, pick_datetime_col


class CallsParser(DataFrameParser):
    def can_parse(self, file_path: str) -> bool:
        low = file_path.lower()
        base = os.path.basename(low)
        return low.endswith((".csv", ".tsv", ".xlsx", ".xls")) and 'call' in base

    def parse_dataframe(self, path_hint: str, df, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        log = context.get('log')
        date_col = next((c for c in ["Date", "date", "Time", "Timestamp", "Call Time", "Date/Time"] if c in df.columns), None)
        if not date_col:
            date_col = pick_datetime_col(df)
        if not date_col:
            if log:
                log(f"No datetime column in calls: {os.path.basename(path_hint)}")
            return out

        type_col = next((c for c in ["Type", "type", "Call Type", "Direction"] if c in df.columns), None)
        name_col = next((c for c in ["Name", "name", "Contact", "Caller Name"] if c in df.columns), None)
        number_col = next((c for c in ["Number", "number", "Phone", "Phone Number", "Address"] if c in df.columns), None)
        dur_col = next((c for c in ["Duration", "duration", "Duration(s)", "Duration (s)", "Call Duration"] if c in df.columns), None)

        for _, r in df.iterrows():
            ts = parse_timestamp(str(r.get(date_col)))
            if not ts:
                continue
            ctype = str(r.get(type_col, '') or '').strip() if type_col else ''
            name = str(r.get(name_col, '') or '').strip() if name_col else ''
            number = str(r.get(number_col, '') or '').strip() if number_col else ''
            dur = str(r.get(dur_col, '') or '').strip() if dur_col else ''
            out.append({
                'mode': 'calls',
                'timestamp': ts.isoformat(sep=' ', timespec='minutes'),
                'time': ts.strftime('%Y-%m-%d %H:%M'),
                'date_str': ts.strftime('%Y-%m-%d %H:%M'),
                'chat': name or number,
                'sender': name,
                'receiver': number,
                'direction': ctype,
                'message': '',
                'body': '',
                'duration': dur,
                'subject': '',
                'category': 'All items',
                'categories': ['All items'],
                'attachment_name': '',
                'attachment': '',
                'source_file': path_hint,
            })
        if log:
            log(f"Parsed {len(out)} calls from {os.path.basename(path_hint)}")
        return out
