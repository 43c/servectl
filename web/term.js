const view = document.querySelector('#terminal');
const status = document.querySelector('#status');
await document.fonts.load('300 15px "JetBrains Mono NL"');
const term = new Terminal({
  fontFamily: getComputedStyle(view).fontFamily,
  fontSize: 15,
  fontWeight: 300,
  fontWeightBold: 300,
  drawBoldTextInBrightColors: true,
  letterSpacing: 1,
  cursorBlink: true,
  // Ghostty's sunset-sea-lbal-c80 palette.
  theme: {
    background: '#1a1a1a', foreground: '#dcdcdc',
    cursor: '#e0e0e0', cursorAccent: '#1a1a1a',
    selectionBackground: '#454545', selectionForeground: '#e0e0e0',
    black: '#3a3a3a', brightBlack: '#555555',
    red: '#e87977', brightRed: '#f76c6c',
    green: '#b3cd73', brightGreen: '#b0cf59',
    yellow: '#f6da87', brightYellow: '#fcd96b',
    blue: '#7baed4', brightBlue: '#6dafdf',
    magenta: '#eeab7d', brightMagenta: '#f9a66a',
    cyan: '#82c3cf', brightCyan: '#70c6d5',
    white: '#cdcdcd', brightWhite: '#eeeeee'
  }
});
const fit = new FitAddon.FitAddon();
term.loadAddon(fit);
term.open(view);
fit.fit();

const url = new URL('/ws', location.href);
url.protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
const socket = new WebSocket(url);
function send(message) {
  if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify(message));
}
socket.onopen = () => {
  send(['set_size', term.rows, term.cols]);
  term.focus();
};
socket.onmessage = event => {
  const [type, data] = JSON.parse(event.data);
  if (type === 'stdout') term.write(data);
};
socket.onclose = () => {
  term.options.disableStdin = true;
  status.textContent = 'Shell disconnected. Reload to open a new session.';
};
term.onData(data => send(['stdin', data]));
term.onResize(({rows, cols}) => send(['set_size', rows, cols]));
new ResizeObserver(() => fit.fit()).observe(view);
