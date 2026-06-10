import fmt
import record
from commands import _shared


def register(subparsers):
    p = subparsers.add_parser(
        'search',
        help='Search tracked servers by comment/directory/cmdline (all terms must match)',
    )
    p.add_argument('query', nargs='+')
    p.add_argument('-v', '--verbose', action='store_true',
                   help='Show all bindings and cmdline')
    _shared.add_no_sync_flag(p)
    p.set_defaults(func=run)


def run(args):
    _shared.sync_unless_skipped(args)
    terms = [q.lower() for q in args.query]
    matches = []
    for e in record.load():
        haystack = ' '.join([
            e.get('comment', '') or '',
            e.get('directory', '') or '',
            e.get('cmdline', '') or '',
        ]).lower()
        if all(t in haystack for t in terms):
            matches.append(e)
    fmt.print_table(matches, record.is_alive, verbose=args.verbose)
    return 0
