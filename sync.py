"""Reconcile the wserv record with current system state.

For every listening socket owned by us:
  - if its pid (or any ancestor) is already recorded, attach the binding
    to that record (covers `uv run python ...` where the recorded pid is
    the uv wrapper and the actual listener is its child).
  - otherwise adopt as a new entry.

For every recorded entry whose pid is dead and we found no descendant
listener for, drop it.
"""
from datetime import datetime

import config
import record
import scanner


def _ts(epoch):
    if epoch:
        return datetime.fromtimestamp(epoch).strftime('%Y%m%d-%H%M%S')
    return datetime.now().strftime('%Y%m%d-%H%M%S')


def sync():
    """Returns (adopted, updated, pruned)."""
    scanned = scanner.scan_listening()
    entries = record.load()
    by_pid = {int(e.get('pid', -1)): e for e in entries}

    adopted = updated = 0
    matched_record_pids = set()

    for pid, info in list(scanned.items()):
        owner_pid = None
        for ancestor in scanner.ancestor_pids(pid):
            if ancestor in by_pid:
                owner_pid = ancestor
                break

        if owner_pid is not None:
            e = by_pid[owner_pid]
            e['bindings'] = info['bindings']
            if not e.get('cmdline'):
                e['cmdline'] = info.get('cmdline', '')
            matched_record_pids.add(owner_pid)
            updated += 1
            continue

        if config.is_ignored(info):
            continue

        new_entry = {
            'pid': pid,
            'comment': '',
            'directory': info.get('cwd', '') or '',
            'cmdline': info.get('cmdline', ''),
            'bindings': info['bindings'],
            'timestamp': _ts(info.get('start_epoch')),
            'source': 'adopted',
        }
        entries.append(new_entry)
        by_pid[pid] = new_entry
        matched_record_pids.add(pid)
        adopted += 1

    pruned = 0
    kept = []
    for e in entries:
        pid = int(e.get('pid', -1))
        if pid in matched_record_pids:
            kept.append(e)
        elif record.is_alive(pid):
            # Process is alive but not bound (anymore, or never was visible).
            # Keep it — could be a server about to bind or paused.
            kept.append(e)
        else:
            pruned += 1

    record.save(kept)
    return adopted, updated, pruned
