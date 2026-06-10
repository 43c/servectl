import tomllib
from pathlib import Path

CONFIG_DIR = Path.home() / '.config' / 'wserv'
RECORD_FILE = CONFIG_DIR / '.record'
LOGS_DIR = CONFIG_DIR / 'logs'

DEFAULTS = {
    'port': {'min': 10000, 'max': 32000},
    'ignore': {'ports': [], 'cmdline': []},
}


def ensure_dirs():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    if not RECORD_FILE.exists():
        RECORD_FILE.touch()


def _deep_merge(base, override):
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k] = _deep_merge(dict(base[k]), v)
        else:
            base[k] = v
    return base


def _read_toml(path):
    try:
        with open(path, 'rb') as f:
            return tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def load():
    """Read config: defaults <- user toml <- project toml. Project wins."""
    cfg = {k: (dict(v) if isinstance(v, dict) else v) for k, v in DEFAULTS.items()}
    for path in [CONFIG_DIR / 'wserv.toml', Path.cwd() / 'wserv.toml']:
        if path.exists():
            cfg = _deep_merge(cfg, _read_toml(path))
    return cfg


def port_range():
    cfg = load()['port']  # always present: load() starts from DEFAULTS
    return int(cfg['min']), int(cfg['max'])


def is_ignored(scanned):
    cfg = load().get('ignore', {})
    ignore_ports = set(cfg.get('ports', []) or [])
    ignore_cmdline = cfg.get('cmdline', []) or []
    ports = {b['port'] for b in scanned.get('bindings', [])}
    if ports & ignore_ports:
        return True
    cmdline = scanned.get('cmdline', '') or ''
    return any(pat and pat in cmdline for pat in ignore_cmdline)
