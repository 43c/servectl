import sys

import record
import sync as sync_mod


def register(subparsers):
    p = subparsers.add_parser(
        'add-comment',
        help='Append text to a tracked entry\'s comment (--replace to overwrite)',
    )
    p.add_argument('target', type=int, help='port (default) or pid (with --pid)')
    p.add_argument('text', nargs='+')
    p.add_argument('--pid', action='store_true', help='Treat target as pid')
    p.add_argument('--replace', action='store_true', help='Replace instead of append')
    p.add_argument('--sep', default='; ', help='Separator between old and new (default "; ")')
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
        print(f"No tracked entry with {kind} {args.target}.", file=sys.stderr)
        return 1
    if len(entries) > 1:
        print(f"{args.target} matches multiple entries; rerun with --pid <pid>:",
              file=sys.stderr)
        for e in entries:
            print(f"  pid={e.get('pid')} dir={e.get('directory')} "
                  f"comment={e.get('comment')}", file=sys.stderr)
        return 1

    entry = entries[0]
    new_text = ' '.join(args.text)
    existing = entry.get('comment', '') or ''
    comment = new_text if args.replace or not existing else f'{existing}{args.sep}{new_text}'
    record.update_by_pid(entry['pid'], comment=comment)
    print(f"pid {entry['pid']}: {comment}")
    return 0
