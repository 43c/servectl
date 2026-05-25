import sync as sync_mod


def register(subparsers):
    p = subparsers.add_parser(
        'sync',
        help='Scan listening sockets, adopt new pids, prune dead entries',
    )
    p.set_defaults(func=run)


def run(args):
    adopted, updated, pruned = sync_mod.sync()
    print(f'sync: {adopted} adopted, {updated} updated, {pruned} pruned')
    return 0
