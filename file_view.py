"""Directory and editor pages for files selected by the host."""
import codecs
import fcntl
import hashlib
import html
import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import quote_from_bytes

WEB = Path(__file__).with_name('web')
CONTROL = re.compile(r'[\x00-\x08\x0e-\x1a\x1c-\x1f\x7f-\x9f]')
BOMS = [(codecs.BOM_UTF32_LE, 'utf-32-le'), (codecs.BOM_UTF32_BE, 'utf-32-be'),
        (codecs.BOM_UTF8, 'utf-8'), (codecs.BOM_UTF16_LE, 'utf-16-le'),
        (codecs.BOM_UTF16_BE, 'utf-16-be')]


class Files:
    """A staged top-level link represents a target explicitly selected at launch."""

    def __init__(self, root, staged):
        self.root = Path(root).resolve()
        self.targets = {p.name: p.resolve() for p in self.root.iterdir()} if staged else None

    def path(self, relative):
        parts = Path(relative).parts
        if not parts or Path(relative).is_absolute() or '..' in parts:
            raise ValueError('Invalid file path')
        base = self.root
        if self.targets is not None:
            if parts[0] not in self.targets:
                raise FileNotFoundError(relative)
            base = self.targets[parts[0]]
            parts = parts[1:]
        path = base.joinpath(*parts).resolve()
        if not path.is_relative_to(base) or not path.is_file():
            raise FileNotFoundError(relative)
        return path

    def editable(self, relative):
        try:
            path = self.path(relative)
            with path.open('rb') as stream:
                decode(stream.read(8192), sample=True)
            return os.access(path, os.W_OK)
        except (OSError, ValueError, RuntimeError):
            return False


def decode(data, sample=False):
    if data.startswith(b'%PDF-'):
        raise ValueError('Binary file')
    bom, encoding = next(((b, e) for b, e in BOMS if data.startswith(b)), (b'', 'utf-8'))
    try:
        text = codecs.getincrementaldecoder(encoding)().decode(data[len(bom):], final=not sample)
    except UnicodeDecodeError:
        if bom:
            raise
        encoding = 'cp1252'
        text = data.decode(encoding)
    if CONTROL.search(text):
        raise ValueError('Binary file')
    return text, bom, encoding


def version(data):
    return '"' + hashlib.sha256(data).hexdigest() + '"'


class ChangedOnDisk(Exception):
    pass


def save(path, original_version, text):
    with path.open('r+b') as source:
        fcntl.flock(source, fcntl.LOCK_EX)
        original = source.read()
        metadata = os.fstat(source.fileno())
        if version(original) != original_version or not os.path.samestat(metadata, path.stat()):
            raise ChangedOnDisk
        previous, bom, encoding = decode(original)
        if CONTROL.search(text):
            raise ValueError('Binary content')
        # Preserve mixed line endings when Ace saves an unchanged buffer.
        newline = re.compile(r'\r\n?')
        if newline.sub('\n', text) == newline.sub('\n', previous):
            return original_version
        data = bom + text.encode(encoding)
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
            try:
                tmp.write(data)
                tmp.flush()
                os.fchmod(tmp.fileno(), metadata.st_mode & 0o777)
                if version(path.read_bytes()) != original_version:
                    raise ChangedOnDisk
                os.replace(tmp.name, path)
            finally:
                Path(tmp.name).unlink(missing_ok=True)
        return version(data)


def page(title, body):
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{html.escape(title)}</title><link rel="stylesheet" href="/__wserv/ui.css">'
            f'</head><body>{body}</body></html>').encode('utf-8', errors='replace')


def listing(directory, relative, files, editing):
    rows = []
    for item in sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.casefold())):
        folder = item.is_dir()
        name = html.escape(item.name) + ('/' if folder else '')
        href = quote_from_bytes(os.fsencode(item.name))
        edit = ''
        if editing and files.editable(relative / item.name):
            edit = f'<a href="{href}?edit" aria-label="Edit {html.escape(item.name)}">Edit</a>'
        try:
            size = f'{item.stat().st_size:,}' if item.is_file() else ''
        except OSError:
            size = ''
        if folder:
            href += '/?list'
        rows.append(f'<tr><td><a href="{href}">{name}</a></td><td>{size}</td><td>{edit}</td></tr>')
    path = '/' if relative == Path('.') else '/' + relative.as_posix() + '/'
    if files.targets is None:
        path = files.root.name + path
    parent = '<a href="../?list">Parent directory</a>' if relative.parts else ''
    content = ('<table><thead><tr><th>Name</th><th>Bytes</th><th></th></tr></thead><tbody>'
               + ''.join(rows) + '</tbody></table>') if rows else '<p>Empty directory.</p>'
    return page(path, f'<main><h1>{html.escape(path)}</h1>{parent}{content}</main>')


def editor(path, relative, back):
    data = path.read_bytes()
    text, _, _ = decode(data)
    document = json.dumps(dict(text=text, version=version(data), name=path.name)).replace('<', r'\u003c')
    label = html.escape('/' + relative)
    return page('Edit ' + relative, f'''<section class="workspace">
<header><a href="{back}">Back</a><h1>{label}</h1>
<button id="save">save</button><button id="undo">undo</button><button id="redo">redo</button></header>
<div id="editor" aria-label="File contents"></div>
<footer><label><input id="vim" type="checkbox" checked> Vim mode</label><span id="mode"></span>
<output id="status" role="status"></output></footer>
</section><script type="application/json" id="document">{document}</script>
<script src="/__wserv/vendor/ace/ace.js"></script>
<script src="/__wserv/vendor/ace/ext-modelist.js"></script>
<script src="/__wserv/vendor/ace/keybinding-vim.js"></script>
<script src="/__wserv/editor.js"></script>''')
