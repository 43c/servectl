import record


def register(subparsers):
    p = subparsers.add_parser(
        'prune',
        help='Drop record entries whose pid is no longer alive',
    )
    p.set_defaults(func=run)


def run(args):
    entries = record.load()
    kept = [e for e in entries if record.is_alive(e.get('pid'))]
    dropped = len(entries) - len(kept)
    record.save(kept)
    print(f'prune: {dropped} dropped, {len(kept)} kept')
    return 0
