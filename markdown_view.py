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
<link rel="stylesheet" href="/__wserv/sunset.css">
<style>
:root {{font-size:17px; line-height:1.65}}
main {{max-width:76ch; margin:auto; padding:clamp(1rem,4vw,3rem); overflow-wrap:anywhere}}
h1,h2,h3 {{line-height:1.25}} img,svg {{max-width:100%}}
pre,blockquote,th,td {{padding:.4em .8em}}
pre,code {{background:var(--sunset-black)}}
pre {{overflow:auto}} blockquote {{margin-left:0; border-left:3px solid var(--sunset-blue)}}
pre:has(> svg) {{background:transparent}}
hr {{border:0; border-top:1px solid var(--sunset-brightBlack)}}
table {{border-collapse:collapse; display:block; overflow:auto}} th,td {{border:1px solid var(--sunset-brightBlack)}}
</style></head><body><main>{content}</main>'''
    if any(t.type == 'fence' and t.info.split()[:1] == ['mermaid'] for t in tokens):
        body += '''<script src="/__wserv/vendor/mermaid.min.js"></script><script type="module">
await document.fonts.ready;
const style = getComputedStyle(document.body);
const color = key => style.getPropertyValue('--sunset-' + key).trim();
const series = ['blue', 'magenta', 'green', 'yellow', 'cyan', 'red',
                'brightBlue', 'brightMagenta', 'brightGreen', 'brightYellow', 'brightCyan', 'brightRed'].map(color);
mermaid.initialize({
    startOnLoad: false, theme: 'base', fontFamily: style.fontFamily,
    themeVariables: {
        darkMode: true, background: color('background'), textColor: color('foreground'),
        primaryColor: color('black'), primaryTextColor: color('foreground'), primaryBorderColor: color('blue'),
        secondaryColor: color('black'), secondaryTextColor: color('foreground'), secondaryBorderColor: color('cyan'),
        tertiaryColor: color('background'), tertiaryTextColor: color('foreground'), tertiaryBorderColor: color('magenta'),
        lineColor: color('white'), edgeLabelBackground: color('background'),
        noteBkgColor: color('black'), noteTextColor: color('foreground'), noteBorderColor: color('yellow'),
        ...Object.fromEntries(series.map((value, i) => ['pie' + (i + 1), value])),
        pieSectionTextColor: color('background'), pieLegendTextColor: color('foreground'),
        xyChart: {backgroundColor: color('background'), plotColorPalette: series.join(',')}
    }
});
const nodes = [];
for (const code of document.querySelectorAll('pre > code.language-mermaid')) {
    const pre = code.parentElement;
    pre.textContent = code.textContent;
    nodes.push(pre);
}
await mermaid.run({nodes});
</script>'''
    return (body + '</body></html>').encode(), assets
