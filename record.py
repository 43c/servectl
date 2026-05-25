import json
import os

import config


def _migrate(entry):
    """Backfill new fields on old-style entries (port-only, no bindings)."""
    if 'bindings' not in entry and 'port' in entry:
        entry['bindings'] = [{
            'family': 'tcp4',
            'addr': '0.0.0.0',
            'port': int(entry['port']),
        }]
    entry.setdefault('source', 'spawned' if entry.get('log') else 'adopted')
    return entry


def load():
    config.ensure_dirs()
    entries = []
    with open(config.RECORD_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(_migrate(json.loads(line)))
            except json.JSONDecodeError:
                continue
    return entries


def save(entries):
    config.ensure_dirs()
    with open(config.RECORD_FILE, 'w') as f:
        for e in entries:
            f.write(json.dumps(e) + '\n')


def add(entry):
    entries = load()
    entries.append(entry)
    save(entries)


def remove_pid(pid):
    entries = load()
    new_entries = [e for e in entries if int(e.get('pid', -1)) != int(pid)]
    save(new_entries)
    return len(entries) - len(new_entries)


def find_by_port(port):
    """Return entries with a binding on `port`."""
    port = int(port)
    matches = []
    for e in load():
        for b in e.get('bindings', []):
            if int(b.get('port', -1)) == port:
                matches.append(e)
                break
    return matches


def find_by_pid(pid):
    pid = int(pid)
    for e in load():
        if int(e.get('pid', -1)) == pid:
            return e
    return None


def update_by_pid(pid, **fields):
    entries = load()
    pid = int(pid)
    for i, e in enumerate(entries):
        if int(e.get('pid', -1)) == pid:
            e.update(fields)
            entries[i] = e
            save(entries)
            return True
    return False


def is_alive(pid):
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True
