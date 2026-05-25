def _fmt_binding(b):
    addr = b.get('addr', '?')
    port = b.get('port', '?')
    if b.get('family') == 'tcp6' and ':' in addr:
        return f'[{addr}]:{port}'
    return f'{addr}:{port}'


def _bindings_str(entry, all_=False):
    bs = entry.get('bindings') or []
    if not bs:
        return '-'
    if all_:
        return ','.join(_fmt_binding(b) for b in bs)
    return _fmt_binding(bs[0])


def _primary_port(entry):
    bs = entry.get('bindings') or []
    if bs:
        return bs[0].get('port', '')
    return entry.get('port', '')


def _row(entry, alive, verbose):
    base = [
        str(_primary_port(entry)),
        _bindings_str(entry, all_=verbose),
        str(entry.get('pid', '')),
        'yes' if alive else 'no',
        entry.get('source', '-') or '-',
        entry.get('comment', '') or '-',
        entry.get('directory', '') or '-',
        entry.get('timestamp', '') or '-',
    ]
    if verbose:
        base.append(entry.get('cmdline', '') or '-')
    return base


def print_table(entries, alive_fn, verbose=False):
    headers = ['PORT', 'ADDRESS', 'PID', 'ALIVE', 'SOURCE', 'COMMENT', 'DIRECTORY', 'STARTED']
    if verbose:
        headers = headers + ['CMDLINE']
    if not entries:
        print('(none)')
        return
    entries = sorted(entries, key=lambda e: (int(_primary_port(e) or 0), int(e.get('pid') or 0)))
    rows = [_row(e, alive_fn(e.get('pid')), verbose) for e in entries]
    widths = [max(len(h), max(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
    sep = '  '

    def fmt_row(r):
        return sep.join(r[i].ljust(widths[i]) for i in range(len(headers)))

    print(fmt_row(headers))
    print(sep.join('-' * w for w in widths))
    for r in rows:
        print(fmt_row(r))
