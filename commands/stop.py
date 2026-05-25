import os
import signal
import sys

import record
import staging as staging_mod
import sync as sync_mod


def register(subparsers):
    p = subparsers.add_parser(
        'stop',
        help='Stop a tracked server by port (or --pid for direct pid)',
    )
    p.add_argument('target', type=int, help='port (default) or pid (with --pid)')
    p.add_argument('--pid', action='store_true', help='Treat target as pid')
    p.add_argument('--no-sync', action='store_true', help='Skip auto-sync')
    p.set_defaults(func=run)


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
        print(f"No tracked server with {kind} {args.target}.", file=sys.stderr)
        return 1

    if len(entries) > 1:
        print(f"Port {args.target} matches multiple entries; rerun with --pid <pid>:",
              file=sys.stderr)
        for e in entries:
            print(f"  pid={e.get('pid')} dir={e.get('directory')} "
                  f"comment={e.get('comment')}", file=sys.stderr)
        return 1

    entry = entries[0]
    pid = entry.get('pid')
    if pid:
        try:
            if entry.get('source') == 'spawned':
                # Spawned with start_new_session=True; kill the whole session
                # so any child workers (e.g. python under `uv run`) go too.
                os.killpg(os.getpgid(int(pid)), signal.SIGTERM)
            else:
                os.kill(int(pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
        except PermissionError as e:
            print(f"Cannot signal pid {pid}: {e}", file=sys.stderr)
            return 1

    staging_dir = entry.get('staging_dir')
    if staging_dir:
        staging_mod.cleanup(staging_dir)

    record.remove_pid(pid)
    print(f"Stopped pid {pid}.")
    return 0
