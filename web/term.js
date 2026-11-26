const view = document.querySelector('#terminal');
const status = document.querySelector('#status');
const font = getComputedStyle(view).fontFamily;
const touch = matchMedia('(pointer: coarse)').matches;
const viewport = window.visualViewport;
if (touch && viewport) {
  function sizeToViewport() {
    if (viewport.scale === 1) document.body.style.height = viewport.height + 'px';
  }
  sizeToViewport();
  viewport.addEventListener('resize', sizeToViewport);
}
const term = new Terminal({
  fontFamily: 'monospace',
  fontSize: 15,
  fontWeight: 300,
  fontWeightBold: 300,
  drawBoldTextInBrightColors: false,
  letterSpacing: 1,
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
document.fonts.load('300 15px "JetBrains Mono NL"').then(() => {
  term.options.fontFamily = font;
  fit.fit();
}, () => {}); // Keep using monospace if the font cannot load.

const url = new URL('/ws', location.href);
url.protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
status.textContent = 'Connecting to shell…';
const socket = new WebSocket(url);
function send(message) {
  if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify(message));
}
socket.onopen = () => {
  send(['set_size', term.rows, term.cols]);
  status.textContent = 'Waiting for shell…';
  if (!touch) term.focus();
};
socket.onmessage = event => {
  const [type, data] = JSON.parse(event.data);
  if (type === 'stdout' && data) {
    status.textContent = '';
    term.write(data);
  }
};
socket.onclose = () => {
  term.options.disableStdin = true;
  status.textContent = 'Shell disconnected. Reload to open a new session.';
};
term.onData(data => send(['stdin', data]));
term.onResize(({rows, cols}) => send(['set_size', rows, cols]));
const observer = new ResizeObserver(() => requestAnimationFrame(() => fit.fit()));
observer.observe(view);
observer.observe(term.element.querySelector('.xterm-screen'));
