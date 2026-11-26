const file = JSON.parse(document.querySelector('#document').textContent);
const editor = ace.edit('editor', {showPrintMargin: false, useWorker: false});
ace.config.set('basePath', '/__wserv/vendor/ace');
editor.session.setMode(ace.require('ace/ext/modelist').getModeForPath(file.name).mode);
editor.setValue(file.text, -1);
editor.setOption('fontFamily', getComputedStyle(document.documentElement).fontFamily);
ace.config.setModuleUrl('ace/theme/sunset', '/__wserv/theme-sunset.js');
editor.setTheme('ace/theme/sunset');
document.fonts.ready.then(() => editor.renderer.updateFontSize());

const status = document.querySelector('#status');
const button = document.querySelector('#save');
let saved = editor.getValue();
editor.on('change', () => {
  status.textContent = 'Modified';
});
window.addEventListener('beforeunload', event => {
  if (editor.getValue() !== saved) event.preventDefault();
});

async function save() {
  if (button.disabled) return;
  const text = editor.getValue();
  button.disabled = true;
  try {
    const response = await fetch(location.href, {
      method: 'PUT', headers: {'If-Match': file.version, 'Content-Type': 'text/plain;charset=utf-8'}, body: text
    });
    if (!response.ok) throw new Error(await response.text());
    file.version = response.headers.get('ETag');
    saved = text;
    status.textContent = saved === editor.getValue() ? 'Saved' : 'Modified';
  } catch (error) {
    status.textContent = error.message;
  } finally {
    button.disabled = false;
    editor.focus();
  }
}
button.addEventListener('click', save);
editor.commands.addCommand({name: 'save', bindKey: {win: 'Ctrl-S', mac: 'Command-S'}, exec: save});
ace.require('ace/keyboard/vim').Vim.defineEx('write', 'w', save);
editor.setKeyboardHandler('ace/keyboard/vim');
function showMode() {
  const mode = editor.getKeyboardHandler().getStatusText(editor) || 'NORMAL';
  document.querySelector('#mode').textContent = 'Vim · ' + mode;
}
editor.on('changeStatus', showMode);
showMode();
editor.focus();
