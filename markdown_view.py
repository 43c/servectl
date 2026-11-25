"""Render one Markdown document and collect the local files it references."""
import html
import re
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

from markdown_it import MarkdownIt


def render(source):
    parser = MarkdownIt('gfm-like', {'html': False})
    tokens = parser.parse(source.read_text(encoding='utf-8-sig'))
    base = source.parent.resolve()
    assets = {}
    headings = set()
    for token in tokens:
        if token.type != 'inline':
            continue
        for child in token.children:
            attr = {'image': 'src', 'link_open': 'href'}.get(child.type)
            if not attr:
                continue
            try:
                url = urlsplit(child.attrGet(attr))
            except ValueError:
                continue
            path = Path(unquote(url.path))
            if url.scheme or url.netloc or not url.path or path.is_absolute():
                continue
            try:
                local = (base / path).resolve()
                relative = local.relative_to(base)
                exists = local.is_file()
            except (OSError, ValueError, RuntimeError):
                continue
            if exists:
                route = f'/__wserv/assets/{relative.as_posix()}'
                assets[route] = local
                child.attrSet(attr, url._replace(path=quote(route)).geturl())

    for i, token in enumerate(tokens):
        if token.type == 'heading_open':
            slug = re.sub(r'[^\w -]', '', tokens[i + 1].content.lower()).replace(' ', '-')
            anchor = slug
            n = 1
            while anchor in headings:
                anchor = f'{slug}-{n}'
                n += 1
            token.attrSet('id', anchor)
            headings.add(anchor)

    content = parser.renderer.render(tokens, parser.options, {})
    body = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(source.name)}</title>
<style>
:root {{color-scheme:light dark; font:17px/1.65 system-ui,sans-serif}}
main {{max-width:76ch; margin:auto; padding:clamp(1rem,4vw,3rem); overflow-wrap:anywhere}}
h1,h2,h3 {{line-height:1.25}} img,svg {{max-width:100%}}
pre,blockquote,th,td {{padding:.4em .8em}}
pre,code {{background:color-mix(in srgb, CanvasText 7%, Canvas); border-radius:.25em}}
pre {{overflow:auto}} blockquote {{margin-left:0; border-left:3px solid GrayText}}
table {{border-collapse:collapse; display:block; overflow:auto}} th,td {{border:1px solid GrayText}}
</style></head><body><main>{content}</main>'''
    if any(t.type == 'fence' and t.info.split()[:1] == ['mermaid'] for t in tokens):
        body += '''<script type="module">
import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11.12.2/dist/mermaid.esm.min.mjs';
mermaid.initialize({startOnLoad:false, theme:matchMedia('(prefers-color-scheme:dark)').matches ? 'dark' : 'default'});
const nodes = [];
for (const code of document.querySelectorAll('pre > code.language-mermaid')) {
    const pre = code.parentElement;
    pre.textContent = code.textContent;
    nodes.push(pre);
}
await mermaid.run({nodes});
</script>'''
    return (body + '</body></html>').encode(), assets
