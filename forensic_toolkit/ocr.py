from pathlib import Path

try:
    from PIL import Image, ImageOps, ImageFilter
    import pytesseract
    OCR_OK = True
except Exception:
    OCR_OK = False

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp', '.heic', '.heif', '.gif'}
MIN_W = 720
MIN_H = 1280
TEXT_PREVIEW_MIN_CHARS = 10


def normalize(text: str) -> str:
    return ' '.join((text or '').split()).strip()


def is_image(path: str) -> bool:
    return Path(path).suffix.lower() in IMAGE_EXTS


def _quick_text_check(img) -> tuple[bool, str]:
    """Cheap text presence check before full OCR."""
    try:
        preview = ImageOps.grayscale(img)
        preview = preview.filter(ImageFilter.SHARPEN)
        preview_text = pytesseract.image_to_string(preview, config='--oem 3 --psm 11')
        preview_text = normalize(preview_text)
        return len(preview_text) >= TEXT_PREVIEW_MIN_CHARS, preview_text
    except Exception:
        return False, ''


def ocr_image(path: str):
    out = {
        'width': None,
        'height': None,
        'text_detected': 'unknown',
        'ocr_status': 'not_image',
        'ocr_text': '',
        'reason': '',
    }
    if not OCR_OK:
        out['ocr_status'] = 'ocr_unavailable'
        out['reason'] = 'Pillow or pytesseract is not installed'
        return out
    try:
        img = Image.open(path)
        img = ImageOps.exif_transpose(img)
        w, h = img.size
        out['width'] = w
        out['height'] = h
        if w < MIN_W or h < MIN_H:
            out['text_detected'] = 'not_checked'
            out['ocr_status'] = 'skipped_small'
            out['reason'] = f'skipped because image is {w}x{h}, below 720x1280'
            return out

        text_present, preview_text = _quick_text_check(img)
        out['text_detected'] = 'yes' if text_present else 'no'
        if not text_present:
            out['ocr_status'] = 'skipped_no_text'
            out['reason'] = 'no meaningful text detected during quick text check'
            return out

        text = pytesseract.image_to_string(img, config='--oem 3 --psm 6')
        text = normalize(text)
        if not text and preview_text:
            text = preview_text
        out['ocr_status'] = 'ocr_done' if text else 'ocr_no_text'
        out['ocr_text'] = text
        out['reason'] = '' if text else 'text was detected but no OCR text was extracted'
        return out
    except Exception as e:
        out['ocr_status'] = 'ocr_error'
        out['reason'] = str(e)
        return out
