import fmt
import record
from commands import _shared


def register(subparsers):
    p = subparsers.add_parser('ls', help='List tracked servers (auto-syncs first)')
    p.add_argument('-v', '--verbose', action='store_true',
                   help='Show all bindings and cmdline')
    _shared.add_no_sync_flag(p)
    p.set_defaults(func=run)


def run(args):
    _shared.sync_unless_skipped(args)
    fmt.print_table(record.load(), record.is_alive, verbose=args.verbose)
    return 0
