import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import config
import pdfjs
import picker
import record
import staging

_SERVE_SCRIPT = str(Path(__file__).resolve().parent.parent / '_serve.py')

VIEWERS = {'md': ('Markdown', ('.md', '.markdown')), 'pdfjs': ('PDF', ('.pdf',))}


def register(subparsers):
    viewers = '\n'.join(f'  {name + " FILE":16} View a {label} file.'
                        for name, (label, _) in sorted(VIEWERS.items()))
    p = subparsers.add_parser(
        'host', help='Host a directory, file, or glob set over HTTP',
        description=f'Viewer subcommands:\n{viewers}',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument('target', nargs='?',
                   help='Path/file/glob (comma-separated allowed). Omit to serve CWD.')
    p.set_defaults(viewer=None, func=run)
    _host_options(p)


def viewer_parser(viewer):
    label, _ = VIEWERS[viewer]
    p = argparse.ArgumentParser(prog=f'wserv host {viewer}', description=f'View a {label} file.')
    p.add_argument('target', metavar='FILE')
    p.set_defaults(viewer=viewer, func=run)
    _host_options(p)
    return p


def _host_options(p):
    p.add_argument('--port', type=int, default=None,
                   help='Explicit port (bypasses auto-pick range)')
    p.add_argument('--bind', default='127.0.0.1',
                   help='Address to bind (default 127.0.0.1; use 0.0.0.0 to '
                        'expose on the network)')
    p.add_argument('-m', '--comment', default='',
                   help='Free-form note for the record')
    p.add_argument('--edit', action='store_true',
                   help='Allow text editing on a network bind (automatic on loopback)')
    p.add_argument('--keep-updated', action='store_true',
                   help='Watch files and live-reload browsers via SSE injection')


def _sanitize(s):
    cleaned = re.sub(r'[^A-Za-z0-9._-]+', '-', s).strip('-')
    return cleaned or 'no-comment'


def _pick_port(explicit, bind):
    if explicit is not None:
        return explicit
    lo, hi = config.port_range()
    port = picker.first_free_port(lo, hi, bind)
    if port is None:
        print(f'No free port in [{lo}, {hi}].', file=sys.stderr)
        return None
    return port


def run(args):
    config.ensure_dirs()

    try:
        if args.viewer:
            label, suffixes = VIEWERS[args.viewer]
            path = Path(args.target).expanduser()
            if not path.is_file() or path.suffix.lower() not in suffixes:
                raise ValueError(f'wserv host {args.viewer} requires a single {label} file: '
                                 f'{args.target}')
            root, staging_dir, single_file = staging.stage_file(path)
        else:
            root, staging_dir, single_file = staging.resolve(args.target)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1

    port = _pick_port(args.port, args.bind)
    if port is None:
        staging.cleanup(staging_dir)
        return 1

    for existing in record.find_by_port(port):
        if record.is_alive(existing.get('pid')):
            print(
                f"Port {port} already tracked (pid {existing.get('pid')}, "
                f"dir {existing.get('directory')}).",
                file=sys.stderr,
            )
            staging.cleanup(staging_dir)
            return 1
        record.remove_pid(existing.get('pid'))

    comment = args.comment or ''
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    log_path = config.LOGS_DIR / f"{timestamp}_{port}_{_sanitize(comment)}.log"
    cmd = ['uv', 'run']
    if args.viewer == 'md':
        cmd += ['--with', 'markdown-it-py[linkify]==4.2.0']
    cmd += ['python', _SERVE_SCRIPT,
            '--port', str(port), '--directory', root, '--bind', args.bind]
    if single_file:
        cmd += ['--single-file', single_file]
    if staging_dir:
        cmd += ['--staged']
    if args.edit:
        cmd += ['--edit']
    if args.keep_updated:
        cmd += ['--keep-updated']

    if args.viewer == 'md':
        cmd += ['--markdown']
    elif args.viewer == 'pdfjs':
        try:
            cmd += ['--pdfjs-dir', str(pdfjs.ensure())]
        except Exception as e:
            print(f'wserv: pdf.js fetch failed: {e}', file=sys.stderr)
            staging.cleanup(staging_dir)
            return 1

    with open(log_path, 'a', buffering=1) as log_file:
        proc = subprocess.Popen(
            cmd,
            cwd=os.getcwd(),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )

    entry = {
        'pid': proc.pid,
        'comment': comment,
        'directory': root,
        'target': args.target,
        'staging_dir': staging_dir,
        'single_file': single_file,
        'keep_updated': args.keep_updated,
        'cmdline': ' '.join(cmd),
        'bindings': [{
            'family': 'tcp6' if ':' in args.bind else 'tcp4',
            'addr': args.bind,
            'port': port,
        }],
        'timestamp': timestamp,
        'log': str(log_path),
        'source': 'spawned',
    }
    record.add(entry)

    print(f"Hosting on port {port} (pid {proc.pid}).")
    print(f"  root: {root}")
    if staging_dir:
        print(f"  staged: {args.target}")
    print(f"  log:  {log_path}")
    return 0
