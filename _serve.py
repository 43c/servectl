#!/usr/bin/env python3
"""Internal server for `wserv host`.

Default mode (no --keep-updated):
  Acts as `python -m http.server --directory ROOT` with an optional
  `--single-file NAME` that internally rewrites GET / to GET /<NAME> so
  a single hosted file appears at the root URL with no redirect.

--keep-updated mode adds:
  - A polling file watcher on ROOT (mtime + size, recursive, follows
    symlinks with cycle guard).
  - An SSE endpoint at /__wserv/reload that fires a "reload" event when
    the watcher sees any change.
  - HTML response injection: a tiny <script> at the end of every HTML
    body opens an EventSource and calls location.reload() on the event.
    Applies to user HTML files and the auto-generated directory listing.
  - For single-file hosting where the file isn't HTML, a generated
    wrapper page that embeds the file with the appropriate tag (<img>,
    <video>, <audio>, <embed>, <pre>) so the reload hook has a DOM to
    live in. Non-browser clients (Accept: */* without text/html, e.g.
    curl) still receive the raw file at /.
  - Cache-Control: no-store on every response so reload always re-fetches.
"""
import argparse
import html
import http.server
import mimetypes
import os
import queue
import re
import threading
import time
import urllib.parse

# pdf.js ships these extensions; make sure they have correct MIME types.
mimetypes.add_type('text/javascript', '.mjs')
mimetypes.add_type('application/wasm', '.wasm')


def _sse_script(on_reload_js):
    """Wrap a JS reload handler in the boilerplate every injected script
    shares: a run-once guard plus an EventSource on the reload endpoint."""
    return (
        '<script>(()=>{if(window.__wservReload)return;'
        'window.__wservReload=true;'
        "const es=new EventSource('/__wserv/reload');"
        f"es.addEventListener('reload',{on_reload_js});"
        '})();</script>'
    ).encode('utf-8')


RELOAD_SCRIPT = _sse_script('()=>location.reload()')

_BODY_END_RE = re.compile(rb'</body\s*>', re.IGNORECASE)


class Broker:
    def __init__(self):
        self._subs = []
        self._lock = threading.Lock()

    def subscribe(self):
        q = queue.Queue(maxsize=8)
        with self._lock:
            self._subs.append(q)
        return q

    def unsubscribe(self, q):
        with self._lock:
            try:
                self._subs.remove(q)
            except ValueError:
                pass

    def publish(self, msg):
        with self._lock:
            subs = list(self._subs)
        for q in subs:
            try:
                q.put_nowait(msg)
            except queue.Full:
                pass


def _scan(root):
    out = {}
    visited = set()
    for dirpath, dirnames, filenames in os.walk(root, followlinks=True):
        try:
            real = os.path.realpath(dirpath)
        except OSError:
            continue
        if real in visited:
            dirnames[:] = []
            continue
        visited.add(real)
        for name in filenames:
            p = os.path.join(dirpath, name)
            try:
                s = os.stat(p)
                out[p] = (s.st_mtime_ns, s.st_size)
            except OSError:
                pass
    return out


def _watch(root, broker, interval=0.5):
    state = None
    while True:
        try:
            cur = _scan(root)
            if state is not None and cur != state:
                broker.publish('reload')
            state = cur
        except Exception:
            pass
        time.sleep(interval)


def _is_html_path(p):
    if not p:
        return False
    ctype, _ = mimetypes.guess_type(p)
    return (ctype or '').startswith('text/html')


def _accepts_html(headers):
    return 'text/html' in (headers.get('Accept', '') or '')


# Native-PDF-viewer fallback when pdf.js isn't available. Swapping the
# <embed>'s src in place preserves the viewer instance, so browsers that
# retain page state across src changes (Edge, sometimes) keep position.
PDF_EMBED_RELOAD_SCRIPT = _sse_script(
    '()=>{'
    'const el=document.querySelector(\'embed[type="application/pdf"]\');'
    'if(!el){location.reload();return;}'
    "const u=new URL(el.getAttribute('src'),location.origin);"
    "u.searchParams.set('_t',Date.now());"
    "el.setAttribute('src',u.toString());"
    '}'
)


# pdf.js wrapper: talks to PDFViewerApplication inside the iframe to
# re-open the doc and restore current page after pagesinit. Works
# cross-browser because pdf.js is our own viewer.
def _pdfjs_reload_script(file_url):
    file_url_js = file_url.replace("'", "\\'")
    return _sse_script(
        '()=>{'
        "const iframe=document.getElementById('wsv-pdf');"
        'let app;try{app=iframe.contentWindow.PDFViewerApplication;}catch(e){}'
        'if(!app||!app.eventBus){iframe.src=iframe.src;return;}'
        'const savedPage=app.page;'
        'const restore=()=>{try{app.page=savedPage;}catch(e){}'
        "app.eventBus.off('pagesinit',restore);};"
        "app.eventBus.on('pagesinit',restore);"
        f"app.open({{url:'{file_url_js}?_t='+Date.now()}});"
        '}'
    )


def _inject_with(content, script):
    if script in content:
        return content
    m = _BODY_END_RE.search(content)
    if m:
        return content[:m.start()] + script + content[m.start():]
    return content + script


def _inject(content):
    return _inject_with(content, RELOAD_SCRIPT)


def _wrapper_html(file_url, filename, mime, pdfjs_available):
    safe_name = html.escape(filename)
    # pdf.js path: full-viewport iframe pointed at the bundled viewer.
    if mime == 'application/pdf' and pdfjs_available:
        viewer_src = '/__pdfjs/web/viewer.html?file=' + urllib.parse.quote(file_url)
        body = (
            f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
            f'<title>{safe_name}</title>'
            f'<style>html,body{{margin:0;padding:0;height:100%}}'
            f'#wsv-pdf{{width:100vw;height:100vh;border:0;display:block}}</style>'
            f'</head><body>'
            f'<iframe id="wsv-pdf" src="{viewer_src}"></iframe>'
            f'</body></html>'
        ).encode('utf-8')
        return _inject_with(body, _pdfjs_reload_script(file_url))

    if mime.startswith('image/'):
        media = f'<img src="{file_url}" alt="{safe_name}">'
    elif mime.startswith('video/'):
        media = f'<video src="{file_url}" controls autoplay></video>'
    elif mime.startswith('audio/'):
        media = f'<audio src="{file_url}" controls autoplay></audio>'
    elif mime == 'application/pdf':
        media = f'<embed src="{file_url}" type="application/pdf">'
    elif (mime.startswith('text/')
          or mime in ('application/json', 'application/xml', 'application/javascript')):
        media = (
            f'<pre id="content">Loading…</pre>'
            f'<script>fetch("{file_url}",{{cache:"no-store"}}).then(r=>r.text())'
            f'.then(t=>{{document.getElementById("content").textContent=t}});</script>'
        )
    else:
        media = f'<p><a href="{file_url}">Download {safe_name}</a></p>'
    body = (
        f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        f'<title>{safe_name}</title>'
        f'<style>html,body{{margin:0;padding:0}}'
        f'body{{min-height:100vh;display:flex;align-items:center;justify-content:center;'
        f'background:#111;color:#eee;font-family:system-ui,sans-serif}}'
        f'img,video{{max-width:100vw;max-height:100vh;object-fit:contain}}'
        f'embed{{width:100vw;height:100vh}}'
        f'pre{{width:100vw;height:100vh;margin:0;padding:1rem;box-sizing:border-box;'
        f'overflow:auto;background:#111;color:#eee;'
        f'font-family:ui-monospace,monospace;font-size:14px}}</style>'
        f'</head><body>{media}</body></html>'
    )
    script = PDF_EMBED_RELOAD_SCRIPT if mime == 'application/pdf' else RELOAD_SCRIPT
    return _inject_with(body.encode('utf-8'), script)


def _build_dir_listing(fs_path, url_path):
    try:
        entries = sorted(os.listdir(fs_path), key=lambda a: a.lower())
    except OSError:
        return None
    display = html.escape(urllib.parse.unquote(url_path), quote=False)
    out = [
        '<!DOCTYPE html>',
        '<html lang="en"><head><meta charset="utf-8">',
        f'<title>Directory listing for {display}</title>',
        '</head><body>',
        f'<h1>Directory listing for {display}</h1>',
        '<hr><ul>',
    ]
    for name in entries:
        full = os.path.join(fs_path, name)
        linkname = name + '/' if os.path.isdir(full) else name
        displayname = linkname + ('@' if os.path.islink(full) else '')
        out.append(
            f'<li><a href="{urllib.parse.quote(linkname)}">'
            f'{html.escape(displayname, quote=False)}</a></li>'
        )
    out.append('</ul><hr></body></html>')
    return _inject('\n'.join(out).encode('utf-8'))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--port', type=int, required=True)
    p.add_argument('--directory', required=True)
    p.add_argument('--bind', default='0.0.0.0')
    p.add_argument('--single-file', default=None,
                   help='Rewrite GET / to GET /<single-file> internally')
    p.add_argument('--keep-updated', action='store_true',
                   help='Watch directory + SSE + inject reload script')
    p.add_argument('--pdfjs-dir', default=None,
                   help='If set, mount pdf.js dist at /__pdfjs/ and use it '
                        'for the PDF single-file wrapper')
    args = p.parse_args()

    directory = os.path.abspath(args.directory)
    single_file = args.single_file
    single_url = '/' + urllib.parse.quote(single_file) if single_file else None
    single_local = os.path.join(directory, single_file) if single_file else None
    keep_updated = args.keep_updated
    pdfjs_dir = os.path.abspath(args.pdfjs_dir) if args.pdfjs_dir else None
    pdfjs_root_real = os.path.realpath(pdfjs_dir) if pdfjs_dir else None
    broker = Broker()

    if keep_updated:
        threading.Thread(
            target=_watch, args=(directory, broker), daemon=True
        ).start()

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=directory, **kw)

        def log_message(self, format, *fargs):
            # Suppress noisy paths: SSE keepalive and pdf.js asset requests.
            msg = format % fargs
            if '/__wserv/reload' in msg or '/__pdfjs/' in msg:
                return
            super().log_message(format, *fargs)

        # --- request dispatch (GET and HEAD differ only in writing the body) ---

        def do_GET(self):
            self._dispatch(head=False)

        def do_HEAD(self):
            self._dispatch(head=True)

        def _dispatch(self, head):
            if keep_updated and self.path == '/__wserv/reload':
                return self._serve_sse(head)
            if pdfjs_dir and self.path.startswith('/__pdfjs/'):
                return self._serve_pdfjs(head)
            if single_url and self.path in ('/', ''):
                # In keep-updated mode for non-HTML, browsers get the wrapper;
                # everything else gets the file itself at the root URL.
                if keep_updated and not _is_html_path(single_local) and _accepts_html(self.headers):
                    return self._serve_wrapper(head)
                self.path = single_url
            if keep_updated:
                return self._inject_get(head)
            super().do_HEAD() if head else super().do_GET()

        def _send_body(self, body, ctype, head,
                       cache_control='no-store', last_modified=None):
            self.send_response(200)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', cache_control)
            if last_modified is not None:
                self.send_header('Last-Modified', self.date_time_string(last_modified))
            self.end_headers()
            if not head:
                self.wfile.write(body)

        def _serve_pdfjs(self, head):
            rel = self.path[len('/__pdfjs/'):].split('?', 1)[0].split('#', 1)[0]
            full = os.path.join(pdfjs_dir, rel)
            real = os.path.realpath(full)
            # Containment check (defeats ../ traversal)
            if not (real == pdfjs_root_real
                    or real.startswith(pdfjs_root_real + os.sep)):
                self.send_error(403, 'Forbidden')
                return
            if not os.path.isfile(real):
                self.send_error(404, 'Not found')
                return
            ctype, _ = mimetypes.guess_type(real)
            try:
                with open(real, 'rb') as f:
                    content = f.read()
            except OSError:
                self.send_error(404, 'Not found')
                return
            # pdf.js assets are versioned by directory; let them cache.
            self._send_body(content, ctype or 'application/octet-stream', head,
                            cache_control='public, max-age=86400')

        # --- handlers ---

        def _serve_sse(self, head):
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Connection', 'close')
            self.end_headers()
            if head:
                return
            q = broker.subscribe()
            try:
                self.wfile.write(b'retry: 1500\n\n')
                self.wfile.flush()
                while True:
                    try:
                        msg = q.get(timeout=15)
                    except queue.Empty:
                        self.wfile.write(b': keepalive\n\n')
                        self.wfile.flush()
                        continue
                    self.wfile.write(f'event: reload\ndata: {msg}\n\n'.encode())
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                broker.unsubscribe(q)

        def _serve_wrapper(self, head):
            mime, _ = mimetypes.guess_type(single_local)
            mime = mime or 'application/octet-stream'
            body = _wrapper_html(single_url, single_file, mime,
                                 pdfjs_available=bool(pdfjs_dir))
            self._send_body(body, 'text/html; charset=utf-8', head)

        def _inject_get(self, head):
            fs_path = self.translate_path(self.path)
            if os.path.isdir(fs_path):
                if not self.path.endswith('/'):
                    self.send_response(301)
                    self.send_header('Location', self.path + '/')
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
                for index in ('index.html', 'index.htm'):
                    idx = os.path.join(fs_path, index)
                    if os.path.isfile(idx):
                        fs_path = idx
                        break
                else:
                    body = _build_dir_listing(fs_path, self.path)
                    if body is None:
                        self.send_error(403, 'No permission to list directory')
                        return
                    self._send_body(body, 'text/html; charset=utf-8', head)
                    return

            try:
                with open(fs_path, 'rb') as f:
                    content = f.read()
            except FileNotFoundError:
                self.send_error(404, 'File not found')
                return
            except OSError:
                self.send_error(403, 'Cannot read file')
                return

            ctype = self.guess_type(fs_path)
            if ctype.startswith('text/html') or ctype == 'application/xhtml+xml':
                content = _inject(content)

            try:
                mtime = os.stat(fs_path).st_mtime
            except OSError:
                mtime = None
            self._send_body(content, ctype, head, last_modified=mtime)

    with http.server.ThreadingHTTPServer((args.bind, args.port), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
