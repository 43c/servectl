import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import config
import picker
import record
import staging as staging_mod

_SERVE_SCRIPT = str(Path(__file__).resolve().parent.parent / '_serve.py')


def register(subparsers):
    p = subparsers.add_parser(
        'host',
        help='Host a directory, file, or glob set over http (default verb)',
    )
    p.add_argument('target', nargs='?', default=None,
                   help='Path/file/glob (comma-separated allowed). Omit to serve CWD.')
    p.add_argument('--port', type=int, default=None,
                   help='Explicit port (bypasses auto-pick range)')
    p.add_argument('-m', '--comment', default='',
                   help='Free-form note for the record')
    p.add_argument('--keep-updated', action='store_true',
                   help='Watch files and live-reload browsers via SSE injection')
    p.set_defaults(func=run)


def _sanitize(s):
    cleaned = re.sub(r'[^A-Za-z0-9._-]+', '-', s).strip('-')
    return cleaned or 'no-comment'


def _pick_port(explicit):
    if explicit is not None:
        return explicit
    lo, hi = config.port_range()
    port = picker.first_free_port(lo, hi)
    if port is None:
        print(f'No free port in [{lo}, {hi}].', file=sys.stderr)
        return None
    return port


def run(args):
    config.ensure_dirs()

    try:
        root, staging_dir, single_file = staging_mod.resolve(args.target)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1

    port = _pick_port(args.port)
    if port is None:
        staging_mod.cleanup(staging_dir)
        return 1

    for existing in record.find_by_port(port):
        if record.is_alive(existing.get('pid')):
            print(
                f"Port {port} already tracked (pid {existing.get('pid')}, "
                f"dir {existing.get('directory')}).",
                file=sys.stderr,
            )
            staging_mod.cleanup(staging_dir)
            return 1
        record.remove_pid(existing.get('pid'))

    comment = args.comment or ''
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    log_path = config.LOGS_DIR / f"{timestamp}_{port}_{_sanitize(comment)}.log"
    cmd = ['uv', 'run', 'python', _SERVE_SCRIPT,
           '--port', str(port), '--directory', root]
    if single_file:
        cmd += ['--single-file', single_file]
    if args.keep_updated:
        cmd += ['--keep-updated']

    log_file = open(log_path, 'a', buffering=1)
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=os.getcwd(),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    finally:
        log_file.close()

    entry = {
        'pid': proc.pid,
        'comment': comment,
        'directory': root,
        'target': args.target,
        'staging_dir': staging_dir,
        'single_file': single_file,
        'keep_updated': args.keep_updated,
        'cmdline': ' '.join(cmd),
        'bindings': [{'family': 'tcp4', 'addr': '0.0.0.0', 'port': port}],
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
