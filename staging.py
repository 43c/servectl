"""Resolve a `host` target into a directory we can hand to http.server.

target=None              -> serve cwd
target=<existing dir>    -> serve that dir
target=<existing file>   -> stage a tmpdir containing one symlink to the file
target with `,` or globs -> stage a tmpdir of symlinks to each match

Comma-separated targets each get glob-expanded with `~` expansion.
"""
import glob
import os
import shutil
import tempfile


def _has_glob_chars(s):
    return any(c in s for c in '*?[')


def _expand(part):
    """Expand `~` and globs (recursive) for one comma-piece."""
    p = os.path.expanduser(part)
    if _has_glob_chars(p):
        return sorted(glob.glob(p, recursive=True))
    if os.path.exists(p):
        return [p]
    return []


def _unique_name(staging, src):
    base = os.path.basename(os.path.abspath(src).rstrip(os.sep)) or 'item'
    name = base
    stem, ext = os.path.splitext(base)
    counter = 1
    while os.path.lexists(os.path.join(staging, name)):
        name = f'{stem}-{counter}{ext}'
        counter += 1
    return name


def _link_into(staging, src):
    name = _unique_name(staging, src)
    os.symlink(os.path.abspath(src), os.path.join(staging, name))
    return name


def stage_file(path):
    staging = tempfile.mkdtemp(prefix='wserv-stage-')
    return staging, staging, _link_into(staging, path)


def resolve(target):
    """Returns (root_dir, staging_dir_or_None, single_file_name_or_None).

    `single_file_name` is set only when target is one literal file path,
    so the caller can wire a `/` -> `/<file>` rewrite. Globs and
    comma-lists always return None for that slot, even if they happen
    to resolve to one match.

    Raises ValueError if target is given but matches nothing.
    """
    if target is None:
        return os.getcwd(), None, None

    is_multi = ',' in target
    has_glob = _has_glob_chars(target)

    if not is_multi and not has_glob:
        p = os.path.abspath(os.path.expanduser(target))
        if not os.path.exists(p):
            raise ValueError(f'target not found: {target}')
        if os.path.isdir(p):
            return p, None, None
        return stage_file(p)

    staging = tempfile.mkdtemp(prefix='wserv-stage-')
    matched = 0
    for part in (s.strip() for s in target.split(',')):
        if not part:
            continue
        for m in _expand(part):
            _link_into(staging, m)
            matched += 1
    if not matched:
        shutil.rmtree(staging, ignore_errors=True)
        raise ValueError(f'no matches for target: {target}')
    return staging, staging, None


def cleanup(staging_dir):
    if staging_dir and os.path.isdir(staging_dir):
        shutil.rmtree(staging_dir, ignore_errors=True)
