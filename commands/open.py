import shutil
import subprocess
import sys

import record
import sync as sync_mod


def register(subparsers):
    p = subparsers.add_parser(
        'open',
        help='Open a tracked server in the default browser (via xdg-open)',
    )
    p.add_argument('target', type=int, help='port (default) or pid (with --pid)')
    p.add_argument('--pid', action='store_true', help='Treat target as pid')
    p.add_argument('--host', default=None,
                   help='Override hostname (default: localhost for 0.0.0.0, else bound addr)')
    p.add_argument('--no-sync', action='store_true', help='Skip auto-sync')
    p.set_defaults(func=run)


def _hostname(addr, override):
    if override:
        return override
    if addr in ('0.0.0.0', '::', '[::]'):
        return 'localhost'
    if ':' in addr and not addr.startswith('['):
        return f'[{addr}]'
    return addr


def run(args):
    if not args.no_sync:
        sync_mod.sync()

    if args.pid:
        e = record.find_by_pid(args.target)
        entries = [e] if e else []
    else:
        entries = record.find_by_port(args.target)

    if not entries:
        kind = 'pid' if args.pid else 'port'
        print(f"No tracked entry with {kind} {args.target}.", file=sys.stderr)
        return 1
    if len(entries) > 1:
        print(f"{args.target} matches multiple entries; rerun with --pid <pid>.",
              file=sys.stderr)
        return 1

    entry = entries[0]
    bs = entry.get('bindings') or []
    if not bs:
        print(f"pid {entry.get('pid')} has no known bindings.", file=sys.stderr)
        return 1
    b = bs[0]
    url = f"http://{_hostname(b.get('addr', ''), args.host)}:{b.get('port')}/"

    opener = shutil.which('xdg-open') or shutil.which('open')
    if not opener:
        print(url)
        return 0
    subprocess.Popen([opener, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(url)
    return 0
