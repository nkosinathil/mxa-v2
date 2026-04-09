import re
import chardet
import pandas as pd
from datetime import datetime
from typing import Optional


def detect_encoding(path: str) -> str:
    try:
        with open(path, 'rb') as f:
            raw = f.read(10000)
        enc = chardet.detect(raw).get('encoding')
        return enc or 'utf-8'
    except Exception:
        return 'utf-8'


def parse_timestamp(val: str) -> Optional[datetime]:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    s = re.sub(r'^Date:\s*', '', s, flags=re.I).strip()
    formats = [
        '%m/%d/%Y %H:%M:%S', '%m/%d/%Y %H:%M', '%m/%d/%Y %I:%M %p', '%m/%d/%y %H:%M',
        '%Y/%m/%d %H:%M:%S', '%Y/%m/%d %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M',
        '%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M', '%d/%m/%y %H:%M', '%d/%m/%y %H:%M:%S',
    ]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    try:
        dt = pd.to_datetime(s, errors='coerce')
        return None if pd.isna(dt) else dt.to_pydatetime()
    except Exception:
        return None


def pick_datetime_col(df: pd.DataFrame):
    if df is None or df.empty:
        return None
    sample = df.head(200)
    best_col = None
    best_hits = 0
    for col in df.columns:
        non_null = 0
        hits = 0
        for val in sample[col]:
            if pd.isna(val):
                continue
            non_null += 1
            if parse_timestamp(str(val)) is not None:
                hits += 1
        if non_null >= 5 and hits / max(1, non_null) >= 0.6:
            return col
        if hits > best_hits:
            best_col = col
            best_hits = hits
    return best_col if best_hits >= 3 else None


def html_escape(s):
    if s is None:
        return ''
    return (str(s)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#039;'))


def slugify(s: str) -> str:
    return re.sub(r'\W+', '_', str(s).lower()).strip('_') or 'item'



def extract_image_exif_metadata(image_path: str) -> dict:
    """Extract EXIF/GPS metadata using the integrated image_metadata module.

    Returns a normalized dict used by photos + mapping functionality.
    """
    out = {
        'gps_lat': None,
        'gps_lon': None,
        'gps_alt': None,
        'gps_timestamp': '',
        'gps_source': 'exif',
        'gps_confidence': None,
        'exif_make': '',
        'exif_model': '',
        'exif_datetime_original': '',
        'has_gps': 0,
        'google_maps_url': '',
        'format': '',
        'size': None,
        'mode': '',
    }
    try:
        from .image_metadata import extract_image_info
        info = extract_image_info(str(image_path)) or {}
    except Exception:
        return out

    if info.get('error'):
        return out

    out['format'] = str(info.get('format') or '')
    out['size'] = info.get('size')
    out['mode'] = str(info.get('mode') or '')
    exif = info.get('exif') or {}
    out['exif_make'] = str(exif.get('Make') or '')
    out['exif_model'] = str(exif.get('Model') or '')
    out['exif_datetime_original'] = str(exif.get('DateTimeOriginal') or exif.get('DateTime') or '')
    out['gps_timestamp'] = out['exif_datetime_original']
    gps = info.get('gps') or {}
    lat = gps.get('latitude')
    lon = gps.get('longitude')
    if lat is not None and lon is not None:
        try:
            out['gps_lat'] = float(lat)
            out['gps_lon'] = float(lon)
            out['has_gps'] = 1
            out['gps_confidence'] = 1.0
            out['google_maps_url'] = str(gps.get('google_maps_url') or '')
        except Exception:
            pass
    return out

    def _rat(x):
        try:
            return float(x[0]) / float(x[1])
        except Exception:
            try:
                return float(x)
            except Exception:
                try:
                    return float(getattr(x, 'num')) / float(getattr(x, 'den'))
                except Exception:
                    return None

    def _deg(dms, ref):
        try:
            d = _rat(dms[0]) or 0
            m = _rat(dms[1]) or 0
            s = _rat(dms[2]) or 0
            sign = -1 if str(ref).upper() in ('S', 'W') else 1
            return sign * (d + m / 60 + s / 3600)
        except Exception:
            return None

    try:
        with Image.open(str(image_path)) as im:
            ex = im.getexif()
            if not ex:
                return out
            tags = {v: k for k, v in ExifTags.TAGS.items()}
            out['exif_make'] = str(ex.get(tags.get('Make', -1)) or '')
            out['exif_model'] = str(ex.get(tags.get('Model', -1)) or '')
            out['exif_datetime_original'] = str(ex.get(tags.get('DateTimeOriginal', -1)) or '')
            out['gps_timestamp'] = out['exif_datetime_original']
            gps_info = ex.get(tags.get('GPSInfo', -1))
            if gps_info:
                g = {ExifTags.GPSTAGS.get(k, k): v for k, v in gps_info.items()}
                lat = _deg(g.get('GPSLatitude'), g.get('GPSLatitudeRef')) if 'GPSLatitude' in g and 'GPSLatitudeRef' in g else None
                lon = _deg(g.get('GPSLongitude'), g.get('GPSLongitudeRef')) if 'GPSLongitude' in g and 'GPSLongitudeRef' in g else None
                if lat is not None and lon is not None:
                    out['gps_lat'] = float(f'{lat:.8f}')
                    out['gps_lon'] = float(f'{lon:.8f}')
                    out['has_gps'] = 1
                    out['gps_confidence'] = 1.0
                gps_alt = g.get('GPSAltitude')
                if gps_alt is not None:
                    alt = _rat(gps_alt)
                    out['gps_alt'] = alt
    except Exception:
        return out
    return out
