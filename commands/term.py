import getpass
import os
import sys
from pathlib import Path

from picker import is_loopback
from commands import _server
from commands.open import hostname


def register(subparsers):
    p = subparsers.add_parser('term', help='Open a shell in a browser over HTTP')
    _server.add_options(p)
    auth = p.add_mutually_exclusive_group()
    auth.add_argument('--password', action='store_true', help='Prompt for a password')
    auth.add_argument('--no-auth', action='store_true', help='Skip login on a loopback listener')
    p.set_defaults(func=run)


def run(args):
    try:
        if args.no_auth and not is_loopback(args.bind):
            raise ValueError('--no-auth requires a loopback bind. Use SSH forwarding for remote access.')
        port = _server.pick_port(args)
        script = Path(__file__).resolve().parent.parent / '_term.py'
        cmd = ['uv', 'run', '--no-project', '--with', 'terminado==0.18.1', 'python', str(script),
               '--port', str(port), '--bind', args.bind]
        chosen = None
        if args.password:
            chosen = getpass.getpass('Terminal password: ')
            if not chosen:
                raise ValueError('Password cannot be empty.')
            cmd.append('--password-stdin')
        elif args.no_auth:
            cmd.append('--no-auth')
        startup = _server.launch(args, port, cmd, os.getcwd(), read_startup=True, input_line=chosen)
    except EOFError:
        print('wserv term: password input ended.', file=sys.stderr)
        return 1
    except (ValueError, OSError, RuntimeError) as e:
        print(f'wserv term: {e}', file=sys.stderr)
        return 1
    print(f'  URL:  http://{hostname(args.bind)}:{port}/')
    if not args.no_auth:
        print('  User: wserv')
        if not args.password:
            print(f'  Password: {startup}')
    return 0
