import argparse
import sys
from pathlib import Path

from commands import _server
import pdfjs
import staging

_SERVE_SCRIPT = str(Path(__file__).resolve().parent.parent / '_serve.py')

VIEWERS = {'md': ('Markdown', ('.md', '.markdown')), 'pdfjs': ('PDF', ('.pdf',))}


def register(subparsers):
    viewers = '\n'.join(f'  {name + " FILE":16} View a {label} file.'
                        for name, (label, _) in sorted(VIEWERS.items()))
    p = subparsers.add_parser(
        'host', help='Host a directory, file, or glob set over HTTP',
        description=f'Viewer subcommands:\n{viewers}',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument('target', nargs='?',
                   help='Path/file/glob (comma-separated allowed). Omit to serve CWD.')
    p.set_defaults(viewer=None, func=run)
    _host_options(p)


def viewer_parser(viewer):
    label, _ = VIEWERS[viewer]
    p = argparse.ArgumentParser(prog=f'wserv host {viewer}', description=f'View a {label} file.')
    p.add_argument('target', metavar='FILE')
    p.set_defaults(viewer=viewer, func=run)
    _host_options(p)
    return p


def _host_options(p):
    _server.add_options(p)
    p.add_argument('--edit', action='store_true',
                   help='Allow text editing on a network bind (automatic on loopback)')
    p.add_argument('--keep-updated', action='store_true',
                   help='Watch files and live-reload browsers via SSE injection')


def run(args):
    try:
        port = _server.pick_port(args)
        if args.viewer:
            label, suffixes = VIEWERS[args.viewer]
            path = Path(args.target).expanduser()
            if not path.is_file() or path.suffix.lower() not in suffixes:
                raise ValueError(f'wserv host {args.viewer} requires a single {label} file: '
                                 f'{args.target}')
            root, staging_dir, single_file = staging.stage_file(path)
        else:
            root, staging_dir, single_file = staging.resolve(args.target)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1

    cmd = ['uv', 'run']
    if args.viewer == 'md':
        cmd += ['--with', 'markdown-it-py[linkify]==4.2.0']
    cmd += ['python', _SERVE_SCRIPT,
            '--port', str(port), '--directory', root, '--bind', args.bind]
    if single_file:
        cmd += ['--single-file', single_file]
    if staging_dir:
        cmd += ['--staged']
    if args.edit:
        cmd += ['--edit']
    if args.keep_updated:
        cmd += ['--keep-updated']

    if args.viewer == 'md':
        cmd += ['--markdown']
    elif args.viewer == 'pdfjs':
        try:
            cmd += ['--pdfjs-dir', str(pdfjs.ensure())]
        except Exception as e:
            print(f'wserv: pdf.js fetch failed: {e}', file=sys.stderr)
            staging.cleanup(staging_dir)
            return 1

    try:
        _server.launch(args, port, cmd, root, target=args.target, staging_dir=staging_dir,
                       single_file=single_file, keep_updated=args.keep_updated)
    except OSError as e:
        staging.cleanup(staging_dir)
        print(f'wserv: {e}', file=sys.stderr)
        return 1
    return 0
