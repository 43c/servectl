import argparse
import importlib
import pkgutil
import sys

import commands
from commands import host


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    if len(argv) >= 2 and argv[0] == 'host' and argv[1] in host.VIEWERS:
        args = host.viewer_parser(argv[1]).parse_args(argv[2:])
        return args.func(args) or 0

    parser = argparse.ArgumentParser(
        prog='wserv',
        description='Quick http.server manager backed by `uv run python -m http.server`.',
    )
    subparsers = parser.add_subparsers(dest='command', metavar='COMMAND')

    for _finder, name, _ispkg in pkgutil.iter_modules(commands.__path__):
        if name.startswith('_'):
            continue
        module = importlib.import_module(f'commands.{name}')
        register = getattr(module, 'register', None)
        if callable(register):
            register(subparsers)

    # Shortcut: `wserv <port> [comment...]` -> `wserv host --port <port> -m <comment>`
    if argv and argv[0].isdigit():
        port, rest = argv[0], argv[1:]
        argv = ['host', '--port', port]
        if rest:
            argv += ['-m', ' '.join(rest)]

    args = parser.parse_args(argv)
    if not getattr(args, 'func', None):
        parser.print_help()
        return 1
    return args.func(args) or 0
