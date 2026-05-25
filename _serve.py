#!/usr/bin/env python3
"""Internal server for `wserv host`.

Like `python -m http.server --directory ROOT` plus optional
`--single-file NAME`: a request for `/` is internally rewritten to that
file so it appears at the root URL with no redirect.
"""
import argparse
import http.server
from urllib.parse import quote


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--port', type=int, required=True)
    p.add_argument('--directory', required=True)
    p.add_argument('--bind', default='0.0.0.0')
    p.add_argument('--single-file', default=None,
                   help='Rewrite GET / to GET /<single-file> internally')
    args = p.parse_args()

    single_url = '/' + quote(args.single_file) if args.single_file else None
    directory = args.directory

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=directory, **kw)

        def _rewrite(self):
            if single_url and (self.path == '/' or self.path == ''):
                self.path = single_url

        def do_GET(self):
            self._rewrite()
            super().do_GET()

        def do_HEAD(self):
            self._rewrite()
            super().do_HEAD()

    with http.server.ThreadingHTTPServer((args.bind, args.port), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
