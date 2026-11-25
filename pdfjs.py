"""Lazy fetch + cache of Mozilla's pdf.js prebuilt viewer.

Used by `wserv host pdfjs <file>.pdf` so the embedded viewer
can survive a document refresh with current-page preserved (which the
browser-native PDF viewer can't reliably do across src changes).
"""
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

VERSION = '5.7.284'
URL = f'https://github.com/mozilla/pdf.js/releases/download/v{VERSION}/pdfjs-{VERSION}-dist.zip'
CACHE_ROOT = Path.home() / '.cache' / 'wserv' / 'pdfjs'


def cache_dir():
    return CACHE_ROOT / VERSION


def is_installed():
    return (cache_dir() / 'web' / 'viewer.html').is_file()


def ensure():
    """Returns the path to the extracted dist. Downloads on first call."""
    dest = cache_dir()
    if is_installed():
        return dest
    dest.mkdir(parents=True, exist_ok=True)
    tmp_zip = dest.parent / f'{VERSION}.zip.part'
    print(f'wserv: fetching pdf.js {VERSION} (~6.5 MB)...', file=sys.stderr)
    try:
        urllib.request.urlretrieve(URL, tmp_zip)
        with zipfile.ZipFile(tmp_zip) as zf:
            zf.extractall(dest)
    except Exception:
        # Roll back so a partial extract doesn't look "installed".
        shutil.rmtree(dest, ignore_errors=True)
        if tmp_zip.exists():
            tmp_zip.unlink()
        raise
    tmp_zip.unlink(missing_ok=True)
    return dest
