import os
import signal
import sys

import record
import staging
from commands import _shared


def register(subparsers):
    p = subparsers.add_parser(
        'stop',
        help='Stop a tracked server by port (or --pid for direct pid)',
    )
    _shared.add_target_args(p)
    p.set_defaults(func=run)


def run(args):
    _shared.sync_unless_skipped(args)

    entry = _shared.find_target(args)
    if entry is None:
        return 1

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

    staging.cleanup(entry.get('staging_dir'))
    record.remove_pid(pid)
    print(f"Stopped pid {pid}.")
    return 0
