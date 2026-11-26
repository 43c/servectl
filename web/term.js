const view = document.querySelector('#terminal');
const status = document.querySelector('#status');
await document.fonts.load('300 15px "JetBrains Mono NL"');
const term = new Terminal({
  fontFamily: getComputedStyle(view).fontFamily,
  fontSize: 15,
  fontWeight: 300,
  fontWeightBold: 300,
  drawBoldTextInBrightColors: false,
  letterSpacing: 0,
  cursorBlink: true,
  // Use the normal sunset-sea-lbal-c80 tones for both ANSI ranges.
  theme: {
    background: '#1a1a1a', foreground: '#dcdcdc',
    cursor: '#e0e0e0', cursorAccent: '#1a1a1a',
    selectionBackground: '#454545', selectionForeground: '#e0e0e0',
    black: '#3a3a3a', brightBlack: '#3a3a3a',
    red: '#e87977', brightRed: '#e87977',
    green: '#b3cd73', brightGreen: '#b3cd73',
    yellow: '#f6da87', brightYellow: '#f6da87',
    blue: '#7baed4', brightBlue: '#7baed4',
    magenta: '#eeab7d', brightMagenta: '#eeab7d',
    cyan: '#82c3cf', brightCyan: '#82c3cf',
    white: '#cdcdcd', brightWhite: '#cdcdcd'
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
