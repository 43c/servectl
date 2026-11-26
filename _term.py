"""Authenticated xterm.js frontend to a Terminado PTY per browser connection."""
import argparse
import asyncio
import base64
import mimetypes
import os
import secrets
import shutil
import signal
import sys
import zipfile
from pathlib import Path

from terminado import TermSocket, UniqueTermManager
from tornado.web import Application, RequestHandler

from picker import is_loopback

WEB = Path(__file__).with_name('web')


class LoginRequired:
    def prepare(self):
        expected = self.settings['authorization']
        if expected is None:
            if not is_loopback(self.request.host_name.strip('[]')):
                self.send_error(403)
            return
        header = self.request.headers.get('Authorization', '').encode()
        if not secrets.compare_digest(header, expected):
            self.set_header('WWW-Authenticate', 'Basic realm="wserv terminal", charset="UTF-8"')
            self.set_status(401)
            self.finish('Sign in as wserv with the terminal password.')


class TerminalPage(LoginRequired, RequestHandler):
    def get(self):
        self.set_header('Cache-Control', 'no-store')
        self.set_header('X-Frame-Options', 'DENY')
        self.finish((WEB / 'term.html').read_bytes())


class ShellSocket(LoginRequired, TermSocket):
    pass


class Asset(RequestHandler):
    def get(self, name):
        if name.startswith('vendor/'):
            try:
                data = self.settings['bundle'].read(name.removeprefix('vendor/'))
            except KeyError:
                self.send_error(404)
                return
        else:
            data = (WEB / name).read_bytes()
        self.set_header('Content-Type', mimetypes.guess_type(name)[0] or 'application/octet-stream')
        self.finish(data)


def make_app(manager, credentials, bundle):
    return Application([
        (r'/', TerminalPage),
        (r'/ws', ShellSocket, {'term_manager': manager}),
        (r'/__wserv/(fonts\.css|term\.js|vendor/(?:fonts|xterm)/[\w.-]+)', Asset),
    ], authorization=None if credentials is None else b'Basic ' + credentials, bundle=bundle)


async def serve(args):
    shell = shutil.which(os.environ.get('SHELL') or '/bin/sh')
    if shell is None:
        raise ValueError('Cannot find the configured shell')
    manager = UniqueTermManager(shell_command=[shell], term_settings={'type': 'xterm-256color'},
                                extra_env={'COLORTERM': 'truecolor', 'TMUX': None, 'TMUX_PANE': None})
    credentials = None
    startup = 'ready'
    if args.no_auth:
        if not is_loopback(args.bind):
            raise ValueError('--no-auth requires a loopback bind')
        if args.bind == 'localhost':
            args.bind = '127.0.0.1'
    else:
        if args.password_stdin:
            password = sys.stdin.readline().rstrip('\n')
            if not password:
                raise ValueError('Password cannot be empty')
        else:
            password = startup = secrets.token_urlsafe(24)
        credentials = base64.b64encode(f'wserv:{password}'.encode())
    with zipfile.ZipFile(WEB / 'vendor.zip') as bundle:
        app = make_app(manager, credentials, bundle)
        server = app.listen(args.port, address=args.bind)
        stopped = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, stopped.set)
        # The parent reads this once over a pipe after bind succeeds.
        print(startup, flush=True)
        try:
            await stopped.wait()
        finally:
            server.stop()
            await manager.shutdown()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--bind', required=True)
    auth = parser.add_mutually_exclusive_group()
    auth.add_argument('--password-stdin', action='store_true')
    auth.add_argument('--no-auth', action='store_true')
    asyncio.run(serve(parser.parse_args()))
