"""Launch and track a wserv listener."""
import os
import re
import signal
import subprocess
from datetime import datetime

import config
import picker
import record


def add_options(p):
    p.add_argument('--port', type=int, help='Port to listen on (default: auto-pick)')
    p.add_argument('--bind', default='127.0.0.1',
                   help='Address to bind (default 127.0.0.1)')
    p.add_argument('-m', '--comment', default='', help='Free-form note for the record')


def pick_port(args):
    port = args.port
    if port is None:
        lo, hi = config.port_range()
        port = picker.first_free_port(lo, hi, args.bind)
        if port is None:
            raise ValueError(f'No free port in [{lo}, {hi}].')
    if not 1 <= port <= 65535:
        raise ValueError('Port must be between 1 and 65535.')
    for existing in record.find_by_port(port):
        if record.is_alive(existing.get('pid')):
            raise ValueError(f"Port {port} already tracked (pid {existing['pid']}, "
                             f"dir {existing.get('directory')}).")
        record.remove_pid(existing['pid'])
    return port


def launch(args, port, cmd, root, *, read_startup=False, input_line=None, **details):
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    label = re.sub(r'[^A-Za-z0-9._-]+', '-', args.comment).strip('-') or 'no-comment'
    log_path = config.LOGS_DIR / f'{timestamp}_{port}_{label}.log'
    with log_path.open('a') as log:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE if read_startup else log,
                                stderr=log, stdin=subprocess.PIPE if input_line is not None else subprocess.DEVNULL,
                                start_new_session=True,
                                text=True)
    startup = None
    try:
        if input_line is not None:
            with proc.stdin:
                proc.stdin.write(input_line + '\n')
        if read_startup:
            with proc.stdout:
                startup = proc.stdout.readline().strip()
            if not startup:
                raise RuntimeError(f'Server failed to start. See {log_path}')
        record.add({
            'pid': proc.pid, 'comment': args.comment, 'directory': root,
            'cmdline': ' '.join(cmd), 'timestamp': timestamp, 'log': str(log_path),
            'source': 'spawned',
            'bindings': [{'family': 'tcp6' if ':' in args.bind else 'tcp4',
                          'addr': args.bind, 'port': port}],
            **details,
        })
    except BaseException:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGTERM)
        proc.wait()
        raise
    print(f'Hosting on port {port} (pid {proc.pid}).')
    print(f'  root: {root}')
    if details.get('staging_dir'):
        print(f"  staged: {details['target']}")
    print(f'  log:  {log_path}')
    return startup
