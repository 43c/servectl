# wserv

Serve directories and files off a remote machine over plain HTTP, with a small
registry so you can list, find, and stop everything you've started.

```sh
wserv host ~/reports            # serve a directory on an auto-picked port
wserv host paper.pdf            # serve one file at the root URL
wserv host '*.png,notes/**' -m "design assets"   # globs / comma lists
wserv 18000 quick share         # shorthand for: host --port 18000 -m "quick share"
wserv ls                        # see everything that's running
wserv stop 18000                # stop by port
```

Servers are spawned detached (`uv run python _serve.py ...`), logged under
`~/.config/wserv/logs/`, and tracked in `~/.config/wserv/.record`.

## Commands

| Command | What it does |
| --- | --- |
| `host [TARGET]` | Serve a dir, file, or glob set. Omit TARGET to serve the CWD. |
| `ls` | List tracked servers. |
| `search TERM...` | Filter tracked servers by comment/directory/cmdline. |
| `open PORT` | Open a tracked server in the browser (prints the URL too). |
| `stop PORT` | Stop a tracked server and clean up. |
| `add-comment PORT TEXT...` | Append to an entry's comment (`--replace` to overwrite). |
| `sync` | Reconcile the record with actual listening sockets. |
| `prune` | Drop entries whose pid is dead. |

Commands that take a `PORT` accept `--pid` to address by pid instead (needed
when several entries share a port). `ls`/`search`/`open`/`stop`/`add-comment`
auto-sync first; pass `--no-sync` to skip.

`sync` also *adopts* listening sockets it didn't spawn, so servers you started
by hand show up in `ls` too.

## Live reload

`wserv host --keep-updated` watches the served tree and pushes a reload to
connected browsers over SSE whenever a file changes. Non-HTML single files get
a generated wrapper page (image/video/audio/text/PDF) so there's a DOM for the
reload hook. For PDFs, add `--pdfjs` to use a bundled pdf.js viewer that
preserves the current page across reloads in any browser (fetched once into
`~/.cache/wserv/pdfjs/`).

## Config

Optional TOML at `~/.config/wserv/wserv.toml`, overridden by a `wserv.toml`
in the CWD:

```toml
[port]
min = 10000      # auto-pick range for `host`
max = 32000

[ignore]
ports = [8080]               # never adopt these ports during sync
cmdline = ["jupyter"]        # never adopt processes matching these substrings
```

## Layout

- `wserv` / `cli.py` — entry point; subcommands auto-register from `commands/`.
- `commands/` — one module per subcommand; `_shared.py` holds common plumbing.
- `_serve.py` — the actual HTTP server child process (standalone script).
- `record.py` / `sync.py` / `scanner.py` — the registry and its reconciliation
  with `ss`-discovered listening sockets.
- `staging.py` — resolves a host target into a directory (symlink tmpdir for
  files/globs).
- `picker.py`, `fmt.py`, `config.py`, `pdfjs.py` — port picking, table output,
  config loading, pdf.js fetch/cache.
