"""Plumbing shared by the command modules.

Most commands address one tracked entry by port (or pid with --pid) and
re-sync the record first unless --no-sync is given; the helpers here keep
that logic in one place.
"""
import sys

import record
import sync as sync_mod


def add_no_sync_flag(parser):
    parser.add_argument('--no-sync', action='store_true', help='Skip auto-sync')


def add_target_args(parser):
    """Add the `target` positional plus the --pid and --no-sync flags."""
    parser.add_argument('target', type=int, help='port (default) or pid (with --pid)')
    parser.add_argument('--pid', action='store_true', help='Treat target as pid')
    add_no_sync_flag(parser)


def sync_unless_skipped(args):
    if not args.no_sync:
        sync_mod.sync()


def find_target(args):
    """Resolve args.target to exactly one record entry, or None.

    Prints to stderr when nothing matches or a port matches several pids.
    """
    if args.pid:
        entry = record.find_by_pid(args.target)
        entries = [entry] if entry else []
    else:
        entries = record.find_by_port(args.target)

    if not entries:
        kind = 'pid' if args.pid else 'port'
        print(f'No tracked entry with {kind} {args.target}.', file=sys.stderr)
        return None
    if len(entries) > 1:
        print(f'Port {args.target} matches multiple entries; rerun with --pid <pid>:',
              file=sys.stderr)
        for e in entries:
            print(f"  pid={e.get('pid')} dir={e.get('directory')} "
                  f"comment={e.get('comment')}", file=sys.stderr)
        return None
    return entries[0]
