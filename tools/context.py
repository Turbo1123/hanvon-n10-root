"""Local-only case context. No device serial or user path is shipped."""
import hashlib
import os
from pathlib import Path
import re


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def case_context():
    serial = os.environ.get('N10_EXPECT_USB_SERIAL', '')
    if not re.fullmatch(r'[A-Za-z0-9._:-]{4,128}', serial):
        raise RuntimeError('Set N10_EXPECT_USB_SERIAL to your own USB serial')
    case = os.environ.get('N10_CASE_DIR')
    if not case:
        raise RuntimeError('Set N10_CASE_DIR to a private case directory outside publication')
    base = Path(case).expanduser().resolve()
    if not base.is_dir():
        raise RuntimeError('N10_CASE_DIR must already exist')
    default = Path(__file__).resolve().parents[1] / 'third_party/rkdeveloptool/build/rkdeveloptool'
    rk = Path(os.environ.get('N10_RKDEVELOPTOOL', default)).expanduser().resolve()
    return base, serial, rk
