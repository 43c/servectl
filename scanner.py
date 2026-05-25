"""Discover listening TCP sockets owned by the current user.

Uses `ss -Hntlp`. Lines without a process column are sockets owned by
another user (ss only exposes that info for our own pids without root),
which is exactly the filter we want.
"""
import os
import re
import subprocess

_PROC_RE = re.compile(r'pid=(\d+)')


def _is_loopback(addr):
    return addr == '::1' or addr.startswith('127.')


def _parse_local(local):
    host, _, port = local.rpartition(':')
    if host.startswith('[') and host.endswith(']'):
        host = host[1:-1]
        family = 'tcp6'
    elif ':' in host:
        family = 'tcp6'
    else:
        family = 'tcp4'
    return family, host, int(port)


def _read_cmdline(pid):
    try:
        with open(f'/proc/{pid}/cmdline', 'rb') as f:
            raw = f.read()
    except OSError:
        return ''
    return raw.replace(b'\x00', b' ').decode('utf-8', 'replace').strip()


def _read_cwd(pid):
    try:
        return os.readlink(f'/proc/{pid}/cwd')
    except OSError:
        return ''


def _read_stat(pid):
    """Returns (ppid, starttime_ticks) or (None, None).

    /proc/<pid>/stat fields after `comm` (which is parenthesized): state, ppid,
    pgrp, ..., starttime (post-comm index 19, i.e. the 22nd field overall).
    """
    try:
        with open(f'/proc/{pid}/stat') as f:
            data = f.read()
        rparen = data.rfind(')')
        fields = data[rparen + 2:].split()
        return int(fields[1]), int(fields[19])
    except (OSError, ValueError, IndexError):
        return None, None


def _btime():
    try:
        with open('/proc/stat') as f:
            for line in f:
                if line.startswith('btime '):
                    return int(line.split()[1])
    except OSError:
        pass
    return None


def scan_listening():
    """Return {pid: {pid, bindings, cmdline, cwd, ppid, start_epoch}}.

    Only pids whose process info is visible (i.e., owned by us).
    Loopback bindings are filtered out.
    """
    try:
        out = subprocess.run(
            ['ss', '-Hntlp'],
            capture_output=True, text=True, check=True,
        ).stdout
    except (FileNotFoundError, subprocess.CalledProcessError):
        return {}

    by_pid = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        local = parts[3]
        proc_field = parts[5] if len(parts) >= 6 else ''
        m = _PROC_RE.search(proc_field)
        if not m:
            continue
        pid = int(m.group(1))
        try:
            family, addr, port = _parse_local(local)
        except (ValueError, IndexError):
            continue
        if _is_loopback(addr):
            continue
        entry = by_pid.setdefault(pid, {'pid': pid, 'bindings': []})
        entry['bindings'].append({'family': family, 'addr': addr, 'port': port})

    btime = _btime()
    clk = os.sysconf('SC_CLK_TCK')
    for pid, entry in by_pid.items():
        entry['cmdline'] = _read_cmdline(pid)
        entry['cwd'] = _read_cwd(pid)
        ppid, ticks = _read_stat(pid)
        entry['ppid'] = ppid
        entry['start_epoch'] = (btime + ticks // clk) if (btime and ticks) else None
    return by_pid


def ancestor_pids(pid, max_depth=8):
    """Yield `pid` then each ancestor up to pid 1 or max_depth."""
    seen = set()
    current = pid
    for _ in range(max_depth):
        if not current or current in seen or current == 1:
            return
        yield current
        seen.add(current)
        ppid, _ = _read_stat(current)
        if not ppid or ppid == current:
            return
        current = ppid
