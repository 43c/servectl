"""Rebuild the checked-in browser assets with: python3 web/vendor.py"""
import base64
import hashlib
import io
import tarfile
import urllib.request
import zipfile
from pathlib import Path


def package(name, version, digest):
    url = f'https://registry.npmjs.org/{name}/-/{name}-{version}.tgz'
    with urllib.request.urlopen(url) as response:
        data = response.read()
    if hashlib.sha512(data).digest() != base64.b64decode(digest):
        raise ValueError(f'{name} checksum mismatch')
    return tarfile.open(fileobj=io.BytesIO(data), mode='r:gz')


def include(bundle, archive, source, name):
    entry = zipfile.ZipInfo(name)
    bundle.writestr(entry, archive.extractfile('package/' + source).read(),
                    compress_type=zipfile.ZIP_DEFLATED)


if __name__ == '__main__':
    output = Path(__file__).with_name('vendor.zip')
    tmp = output.with_suffix('.tmp')
    with zipfile.ZipFile(tmp, 'w') as bundle:
        with package('ace-builds', '1.45.2', 'a0IADaETGBnBW5CIkniUJn7F+NyTuHWKqlv1A8FXaMmFflJsMGnU3TzkiyslInqIZ3odfcVKOdXBGIKBefzFDA==') as ace:
            assets = {'ace.js', 'keybinding-vim.js', 'ext-modelist.js', 'ext-searchbox.js'}
            for path in sorted(ace.getnames()):
                parent, _, name = path.rpartition('/')
                if parent == 'package/src-min-noconflict' and (name in assets or name.startswith('mode-')):
                    include(bundle, ace, parent.removeprefix('package/') + '/' + name, 'ace/' + name)
            include(bundle, ace, 'LICENSE', 'ace/LICENSE')
        with package('mermaid', '11.12.2', 'n34QPDPEKmaeCG4WDMGy0OT6PSyxKCfy2pJgShP+Qow2KLrvWjclwbc3yXfSIf4BanqWEhQEpngWwNp/XhZt6w==') as mermaid:
            include(bundle, mermaid, 'dist/mermaid.min.js', 'mermaid.min.js')
            include(bundle, mermaid, 'LICENSE', 'mermaid-LICENSE')
        url = 'https://github.com/JetBrains/JetBrainsMono/releases/download/v2.304/JetBrainsMono-2.304.zip'
        with urllib.request.urlopen(url) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != '6f6376c6ed2960ea8a963cd7387ec9d76e3f629125bc33d1fdcd7eb7012f7bbf':
            raise ValueError('JetBrains Mono checksum mismatch')
        with zipfile.ZipFile(io.BytesIO(data)) as fonts:
            faces = ('Regular', 'Italic', 'Bold', 'BoldItalic')
            paths = [f'fonts/ttf/JetBrainsMonoNL-{face}.ttf' for face in faces]
            for path in ['OFL.txt', *paths]:
                entry = zipfile.ZipInfo('fonts/' + Path(path).name)
                bundle.writestr(entry, fonts.read(path), compress_type=zipfile.ZIP_DEFLATED)
    tmp.replace(output)
