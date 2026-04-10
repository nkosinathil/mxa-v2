"""Audio parser with optional speech-to-text support.

This parser currently targets WhatsApp-style .opus voice notes for transcription.
Transcription is optimized for English and Afrikaans audio.
Supported backends checked in order:
1. faster_whisper
2. whisper (openai-whisper)

If no backend is available, or transcription is disabled, the file is still indexed and a clear note is stored in the body.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from .base import BaseParser

AUDIO_EXTS = {'.opus'}
SUPPORTED_LANGS = ('en', 'af')


def _run_cmd(cmd: List[str]) -> Tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except Exception as exc:
        return 1, '', str(exc)


def _probe_duration_seconds(path: str) -> Optional[float]:
    code, out, _err = _run_cmd([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', path
    ])
    if code != 0 or not out:
        return None
    try:
        return float(out)
    except Exception:
        return None


def _seconds_to_hms(seconds: Optional[float]) -> str:
    if seconds is None:
        return ''
    total = int(round(seconds))
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _convert_to_wav16k(src: str) -> Tuple[Optional[str], Optional[str]]:
    fd, out_path = tempfile.mkstemp(suffix='.wav', prefix='mxa_audio_')
    os.close(fd)
    code, _out, err = _run_cmd([
        'ffmpeg', '-y', '-i', src,
        '-ac', '1', '-ar', '16000', '-vn', out_path
    ])
    if code != 0:
        try:
            os.unlink(out_path)
        except Exception:
            pass
        return None, err or 'ffmpeg conversion failed'
    return out_path, None


def _transcribe_with_faster_whisper(wav_path: str) -> Dict[str, Any]:
    from faster_whisper import WhisperModel  # type: ignore

    model_name = os.environ.get('MXA_WHISPER_MODEL', 'base')
    model = WhisperModel(model_name, device='cpu', compute_type='int8')

    best = None
    for lang in SUPPORTED_LANGS:
        segments, info = model.transcribe(wav_path, vad_filter=True, language=lang)
        parts = []
        for seg in segments:
            txt = (seg.text or '').strip()
            if txt:
                parts.append(txt)
        transcript = ' '.join(parts).strip()
        candidate = {
            'transcript': transcript,
            'language': getattr(info, 'language', None) or lang,
            'language_probability': getattr(info, 'language_probability', None),
            'backend': f'faster_whisper:{model_name}',
        }
        if best is None:
            best = candidate
            continue
        best_prob = best.get('language_probability') or 0
        cand_prob = candidate.get('language_probability') or 0
        if len(transcript) > len(best.get('transcript') or '') or cand_prob > best_prob:
            best = candidate

    return best or {
        'transcript': '',
        'language': None,
        'language_probability': None,
        'backend': f'faster_whisper:{model_name}',
    }


def _transcribe_with_whisper(wav_path: str) -> Dict[str, Any]:
    import whisper  # type: ignore

    model_name = os.environ.get('MXA_WHISPER_MODEL', 'base')
    model = whisper.load_model(model_name)

    best = None
    for lang in SUPPORTED_LANGS:
        result = model.transcribe(wav_path, fp16=False, language=lang)
        candidate = {
            'transcript': (result.get('text') or '').strip(),
            'language': result.get('language') or lang,
            'language_probability': None,
            'backend': f'whisper:{model_name}',
        }
        if best is None or len(candidate['transcript']) > len(best.get('transcript') or ''):
            best = candidate

    return best or {
        'transcript': '',
        'language': None,
        'language_probability': None,
        'backend': f'whisper:{model_name}',
    }


def _try_transcribe(src_path: str) -> Dict[str, Any]:
    wav_path = None
    try:
        wav_path, conv_err = _convert_to_wav16k(src_path)
        if not wav_path:
            return {
                'transcript': '',
                'language': None,
                'language_probability': None,
                'transcribed': False,
                'processing_status': 'failed',
                'skip_reason': conv_err or 'Audio conversion failed',
                'backend': None,
            }

        try:
            data = _transcribe_with_faster_whisper(wav_path)
            data.update({'transcribed': bool(data.get('transcript')), 'processing_status': 'done', 'skip_reason': ''})
            return data
        except Exception as exc:
            faster_err = str(exc)

        try:
            data = _transcribe_with_whisper(wav_path)
            data.update({'transcribed': bool(data.get('transcript')), 'processing_status': 'done', 'skip_reason': ''})
            return data
        except Exception as exc:
            whisper_err = str(exc)

        return {
            'transcript': '',
            'language': None,
            'language_probability': None,
            'transcribed': False,
            'processing_status': 'skipped',
            'skip_reason': (
                'No working transcription backend available. '
                f'faster-whisper: {faster_err or "not available"}; '
                f'openai-whisper: {whisper_err or "not available"}.'
            ),
            'backend': None,
        }
    finally:
        if wav_path and os.path.exists(wav_path):
            try:
                os.unlink(wav_path)
            except Exception:
                pass


class AudioParser(BaseParser):
    def can_parse(self, file_path: str) -> bool:
        return os.path.splitext(file_path)[1].lower() in AUDIO_EXTS

    def parse(self, file_path: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        log = context.get('log')
        p = Path(file_path)
        try:
            st = p.stat()
        except Exception:
            return []

        duration_seconds = _probe_duration_seconds(str(p))
        transcribe_enabled = bool(context.get('transcribe_audio', False))
        max_seconds = context.get('audio_max_transcription_seconds')
        try:
            max_seconds = float(max_seconds) if max_seconds not in (None, '', False) else None
        except Exception:
            max_seconds = None

        if not transcribe_enabled:
            result = {
                'transcript': '',
                'language': None,
                'language_probability': None,
                'transcribed': False,
                'processing_status': 'disabled',
                'skip_reason': 'Transcription disabled. Audio transcription can add significant processing time; enable it only when needed.',
                'backend': None,
            }
        elif max_seconds is not None and duration_seconds is not None and duration_seconds > max_seconds:
            result = {
                'transcript': '',
                'language': None,
                'language_probability': None,
                'transcribed': False,
                'processing_status': 'skipped',
                'skip_reason': f'Transcription skipped because duration exceeds limit of {_seconds_to_hms(max_seconds)}.',
                'backend': None,
            }
        else:
            result = _try_transcribe(str(p))

        transcript = (result.get('transcript') or '').strip()
        body = transcript or '[No transcript available]'

        if callable(log):
            status = 'transcribed' if result.get('transcribed') else result.get('processing_status') or 'queued'
            log(f"[progress] Audio processed: {p.name} ({status})")

        meta = {
            'audio_duration_seconds': duration_seconds,
            'audio_duration': _seconds_to_hms(duration_seconds),
            'transcribed': bool(result.get('transcribed')),
            'language': result.get('language'),
            'language_probability': result.get('language_probability'),
            'speech_ratio': None,
            'has_transcript': bool(transcript),
            'skip_reason': result.get('skip_reason') or '',
            'processing_status': result.get('processing_status') or '',
            'transcription_backend': result.get('backend'),
            'size_bytes': st.st_size,
            'transcription_enabled': transcribe_enabled,
            'audio_max_transcription_seconds': max_seconds,
        }

        return [{
            'mode': 'audio',
            'timestamp': '',
            'time': '',
            'date_str': '',
            'chat': p.stem,
            'chat_type': 'audio',
            'sender': '',
            'receiver': '',
            'direction': '',
            'message': body,
            'body': body,
            'subject': f'Audio Transcript: {p.name}',
            'duration': meta['audio_duration'],
            'conversation_key': p.stem,
            'message_id': p.stem,
            'sequence_no': 0,
            'attachment_name': p.name,
            'attachment': p.name,
            'source_file': str(p.resolve()),
            'ocr_text': '',
            'audio_meta_json': json.dumps(meta, ensure_ascii=False),
            'transcription_status': (result.get('processing_status') or ('transcribed' if result.get('transcribed') else 'skipped')),
            'transcription_reason': result.get('skip_reason') or '',
        }]
