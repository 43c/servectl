import shutil
import subprocess
import sys

from commands import _shared


def register(subparsers):
    p = subparsers.add_parser(
        'open',
        help='Open a tracked server in the default browser (via xdg-open)',
    )
    _shared.add_target_args(p)
    p.add_argument('--host', default=None,
                   help='Override hostname (default: localhost for 0.0.0.0, else bound addr)')
    p.set_defaults(func=run)


def hostname(addr, override=None):
    if override:
        return override
    if addr in ('0.0.0.0', '::', '[::]'):
        return 'localhost'
    if ':' in addr and not addr.startswith('['):
        return f'[{addr}]'
    return addr


def run(args):
    _shared.sync_unless_skipped(args)

    entry = _shared.find_target(args)
    if entry is None:
        return 1

    bindings = entry.get('bindings') or []
    if not bindings:
        print(f"pid {entry.get('pid')} has no known bindings.", file=sys.stderr)
        return 1
    b = bindings[0]
    url = f"http://{hostname(b.get('addr', ''), args.host)}:{b.get('port')}/"

    opener = shutil.which('xdg-open') or shutil.which('open')
    if opener:
        subprocess.Popen([opener, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(url)
    return 0
