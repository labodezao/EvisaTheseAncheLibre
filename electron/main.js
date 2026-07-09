// Enveloppe Electron : application de bureau Windows / macOS / Linux.
const { app, BrowserWindow, session } = require('electron');
const path = require('path');

function createWindow() {
  const win = new BrowserWindow({
    width: 1500,
    height: 950,
    minWidth: 980,
    minHeight: 640,
    backgroundColor: '#14171c',
    title: 'Accordeur Anche Libre Pro',
    webPreferences: {
      contextIsolation: true,
      sandbox: true,
    },
  });
  win.removeMenu?.();
  win.loadFile(path.join(__dirname, '..', 'web', 'index.html'));
}

app.whenReady().then(() => {
  // Autorise le micro (macOS affichera la demande système grâce à
  // NSMicrophoneUsageDescription injecté par electron-builder).
  session.defaultSession.setPermissionRequestHandler((wc, permission, cb) => {
    cb(permission === 'media');
  });
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
