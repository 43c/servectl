import fmt
import record
import sync as sync_mod


def register(subparsers):
    p = subparsers.add_parser('ls', help='List tracked servers (auto-syncs first)')
    p.add_argument('-v', '--verbose', action='store_true',
                   help='Show all bindings and cmdline')
    p.add_argument('--no-sync', action='store_true', help='Skip auto-sync')
    p.set_defaults(func=run)


def run(args):
    if not args.no_sync:
        sync_mod.sync()
    fmt.print_table(record.load(), record.is_alive, verbose=args.verbose)
    return 0
