import record
from commands import _shared


def register(subparsers):
    p = subparsers.add_parser(
        'add-comment',
        help='Append text to a tracked entry\'s comment (--replace to overwrite)',
    )
    _shared.add_target_args(p)
    p.add_argument('text', nargs='+')
    p.add_argument('--replace', action='store_true', help='Replace instead of append')
    p.add_argument('--sep', default='; ', help='Separator between old and new (default "; ")')
    p.set_defaults(func=run)


def run(args):
    _shared.sync_unless_skipped(args)

    entry = _shared.find_target(args)
    if entry is None:
        return 1

    new_text = ' '.join(args.text)
    existing = entry.get('comment', '') or ''
    comment = new_text if args.replace or not existing else f'{existing}{args.sep}{new_text}'
    record.update_by_pid(entry['pid'], comment=comment)
    print(f"pid {entry['pid']}: {comment}")
    return 0
