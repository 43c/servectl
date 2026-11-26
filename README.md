# wserv

Serve directories and files over HTTP, with a registry to list, find, and stop them.

## Install

Needs Python 3.11+, [uv](https://github.com/astral-sh/uv), and `ss` (iproute2).

```sh
git clone https://github.com/<you>/wserv ~/.local/share/wserv
ln -s ~/.local/share/wserv/wserv ~/.local/bin/wserv
```

## Run

```sh
wserv host ~/reports          # serve a directory on an auto-picked port
wserv host paper.pdf          # serve one file at /
wserv host pdfjs paper.pdf    # read with PDF.js
wserv host md notes.md        # read Markdown with tables, links, and Mermaid diagrams
wserv host '*.png,notes/**'   # globs, comma-separated lists
wserv 18000 quick share       # shorthand for: host --port 18000 -m "quick share"
wserv ls                      # list tracked servers
wserv open 18000              # open in browser
wserv stop 18000              # stop by port
```

| Command | |
| --- | --- |
| `host [TARGET]` | Serve a dir, file, or glob set. Omit TARGET for the CWD. |
| `ls` | List tracked servers. |
| `search TERM...` | Filter by comment, directory, or cmdline. |
| `open PORT` | Open in the browser; prints the URL. |
| `stop PORT` | Stop and clean up. |
| `add-comment PORT TEXT...` | Append to a comment (`--replace` to overwrite). |
| `sync` | Reconcile the record with listening sockets. |
| `prune` | Drop entries whose pid is dead. |

`host` flags: `--port`, `-m COMMENT`, `--bind ADDR` (default `127.0.0.1`),
`--keep-updated` (reload on changes, preserving the current page in PDF.js).

Directory listings show filenames, byte sizes, and an **Edit** link for writable
text files, including extensionless files. An existing `index.html` opens as
usual. Visit `/?list` to browse its directory or `/?edit` to edit a single hosted
file. The Markdown viewer also has an **Edit source** link.

Ace opens in Vim normal mode. Press `i` to edit, then `Esc` and `:w` followed by
Enter to save to disk. The **Save** button works in either mode. If another
editor changes the file, wserv keeps your buffer and reports the conflict.

Editing is enabled on loopback. Use `--edit` with a network bind to let anyone
who can reach the server modify the hosted text files. Use editing with trusted
content and clients.

The Markdown viewer serves relative images and file links within the document’s
directory. Use fenced `mermaid` blocks for diagrams and charts.
Ace, its language modes and Vim bindings, Mermaid, and JetBrains Mono NL ship in
`web/vendor.zip`. Run `python3 web/vendor.py` to rebuild from the pinned releases.

Commands taking a `PORT` accept `--pid` to address by pid instead.
`ls`/`search`/`open`/`stop`/`add-comment` sync first; `--no-sync` skips it.

State lives in `~/.config/wserv/` (`.record`, `logs/`).

## Config

`~/.config/wserv/wserv.toml`, overridden by `wserv.toml` in the CWD:

```toml
[port]
min = 10000
max = 32000

[ignore]
ports = [8080]
cmdline = ["jupyter"]
```

## License

MIT.

---

Personal tool for trusted networks only.
