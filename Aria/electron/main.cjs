const { app, BrowserWindow, Menu, dialog, ipcMain, shell } = require("electron");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const { spawn } = require("node:child_process");

const HOST = "127.0.0.1";
const PORTS = [8080, 8081, 8082, 8083, 8084];
const DATA_EXTENSIONS = new Set([".db", ".json", ".sqlite", ".sqlite3", ".txt"]);
const PUBLIC_SITE_PATHS = new Set([
  "/",
  "/home",
  "/features",
  "/docs",
  "/llms.txt",
  "/get-token",
  "/tos",
  "/terms",
  "/privacy",
]);

let backendProcess = null;
let backendStartError = null;
let backendConfigPath = null;
let backendContext = null;
let dashboardUrl = null;
let mainWindow = null;
let tokenWindow = null;

function requestDashboard(port) {
  return new Promise((resolve) => {
    const request = http.get({ hostname: HOST, port, path: "/", timeout: 1200 }, (response) => {
      let html = "";
      response.setEncoding("utf8");
      response.on("data", (chunk) => {
        if (html.length < 8192) html += chunk;
      });
      response.on("end", () => {
        resolve(response.statusCode === 200 && html.includes("<title>Aria |")
          ? `http://${HOST}:${port}`
          : null);
      });
      response.on("error", () => resolve(null));
    });
    request.on("timeout", () => request.destroy());
    request.on("error", () => resolve(null));
  });
}

async function findDashboard() {
  const results = await Promise.all(PORTS.map(requestDashboard));
  return results.find(Boolean) || null;
}

function copyRuntimeData(source, destination) {
  if (!fs.existsSync(source)) return;

  for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
    const sourcePath = path.join(source, entry.name);
    const destinationPath = path.join(destination, entry.name);
    if (entry.isDirectory()) {
      copyRuntimeData(sourcePath, destinationPath);
    } else if (
      DATA_EXTENSIONS.has(path.extname(entry.name).toLowerCase()) ||
      entry.name === ".aria_webpanel_secret" ||
      entry.name === ".aria_key"
    ) {
      fs.mkdirSync(destination, { recursive: true });
      fs.copyFileSync(sourcePath, destinationPath);
    }
  }
}

function preparePackagedBackend() {
  const bundledBackend = path.join(process.resourcesPath, "aria-backend");
  const writableBackend = path.join(app.getPath("userData"), "backend");
  const versionFile = path.join(writableBackend, ".electron-backend-version");
  const installedVersion = fs.existsSync(versionFile)
    ? fs.readFileSync(versionFile, "utf8").trim()
    : "";

  if (installedVersion === app.getVersion()) return writableBackend;
  if (!fs.existsSync(bundledBackend)) {
    throw new Error("The bundled Aria backend is missing. Rebuild the desktop app with npm run dist.");
  }

  const stagedBackend = `${writableBackend}.new`;
  fs.rmSync(stagedBackend, { recursive: true, force: true });
  fs.cpSync(bundledBackend, stagedBackend, { recursive: true });
  copyRuntimeData(writableBackend, stagedBackend);
  fs.writeFileSync(path.join(stagedBackend, ".electron-backend-version"), app.getVersion());
  fs.rmSync(writableBackend, { recursive: true, force: true });
  fs.renameSync(stagedBackend, writableBackend);
  return writableBackend;
}

function getBackendContext() {
  if (backendContext) return backendContext;

  const projectRoot = path.resolve(__dirname, "..");
  const cwd = app.isPackaged ? preparePackagedBackend() : projectRoot;
  const bundledDirectory = path.join(cwd, "_internal");
  backendContext = {
    cwd,
    command: app.isPackaged
      ? path.join(cwd, process.platform === "win32" ? "Aria.exe" : "Aria")
      : process.env.ARIA_PYTHON || (process.platform === "win32" ? "python" : "python3"),
    configPath: path.join(
      app.isPackaged && fs.existsSync(bundledDirectory) ? bundledDirectory : cwd,
      "config.json",
    ),
  };
  backendConfigPath = backendContext.configPath;
  return backendContext;
}

function runBackendScript(scriptName, args = [], options = {}) {
  const context = getBackendContext();
  const scriptArgs = app.isPackaged
    ? ["--aria-run-script", scriptName, ...args]
    : [path.join(context.cwd, scriptName), ...args];
  return spawn(context.command, scriptArgs, {
    cwd: context.cwd,
    env: { ...process.env, ARIA_DESKTOP_MODE: "1", ...options.env },
    stdio: options.stdio || ["ignore", "ignore", "pipe"],
    windowsHide: true,
  });
}

function startBackend(runtimeToken = null) {
  backendStartError = null;
  backendProcess = runBackendScript("aria.py", [], {
    env: { ARIA_TOKEN_STDIN: runtimeToken ? "1" : "0" },
    stdio: ["pipe", "ignore", "ignore"],
  });
  backendProcess.stdin.on("error", () => {});
  backendProcess.stdin.end(runtimeToken ? `${runtimeToken}\n` : "");
  backendProcess.once("error", (error) => {
    backendStartError = error;
  });
}

async function waitForDashboard() {
  const deadline = Date.now() + 45000;
  while (Date.now() < deadline) {
    if (backendStartError) throw backendStartError;
    if (backendProcess.exitCode !== null || backendProcess.signalCode !== null) {
      throw new Error(`Aria backend exited with code ${backendProcess.exitCode ?? backendProcess.signalCode}. Check its Python dependencies and config.`);
    }
    const url = await findDashboard();
    if (url) return url;
    await new Promise((resolve) => setTimeout(resolve, 350));
  }
  throw new Error("Aria's dashboard did not start on ports 8080-8084.");
}

function hasSavedToken() {
  try {
    const config = JSON.parse(fs.readFileSync(backendConfigPath, "utf8"));
    const token = config.token;
    return typeof token === "string" && token.trim() !== "" && token !== "token here";
  } catch {
    return false;
  }
}

function stopBackend() {
  const child = backendProcess;
  backendProcess = null;
  if (!child || child.exitCode !== null || child.signalCode !== null) return Promise.resolve();

  return new Promise((resolve) => {
    const finish = () => {
      clearTimeout(timeout);
      resolve();
    };
    const timeout = setTimeout(finish, 5000);
    child.once("exit", finish);
    child.kill();
  });
}

function saveTokenConfig(token, remember) {
  return new Promise((resolve, reject) => {
    const action = remember ? "save" : "clear";
    const child = runBackendScript("token_config.py", [action], {
      stdio: ["pipe", "ignore", "pipe"],
    });
    let stderr = "";
    child.stderr.on("data", (chunk) => {
      stderr = (stderr + chunk.toString()).slice(-4000);
    });
    child.once("error", reject);
    child.once("exit", (code, signal) => {
      if (code === 0) resolve();
      else reject(new Error(stderr.trim() || `Token configuration helper exited (${code ?? signal}).`));
    });
    child.once("spawn", () => child.stdin.end(remember ? `${token}\n` : "\n"));
    child.stdin.on("error", () => {});
  });
}

function isDashboardUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === "http:"
      && url.hostname === HOST
      && PORTS.includes(Number(url.port))
      && !PUBLIC_SITE_PATHS.has(url.pathname);
  } catch {
    return false;
  }
}

function isPublicWebsiteUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === "http:"
      && url.hostname === HOST
      && PORTS.includes(Number(url.port))
      && PUBLIC_SITE_PATHS.has(url.pathname);
  } catch {
    return false;
  }
}

function openExternalHttps(value) {
  try {
    const url = new URL(value);
    if (url.protocol === "https:" && !url.username && !url.password) {
      shell.openExternal(url.toString());
    }
  } catch {
    return;
  }
}

function createTokenWindow() {
  if (!backendContext) return;
  if (tokenWindow && !tokenWindow.isDestroyed()) {
    tokenWindow.focus();
    return;
  }

  const options = {
    width: 480,
    height: 470,
    resizable: false,
    show: false,
    title: "Connect Aria",
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  };
  if (mainWindow) {
    options.parent = mainWindow;
    options.modal = true;
  }

  tokenWindow = new BrowserWindow(options);
  tokenWindow.once("ready-to-show", () => tokenWindow.show());
  tokenWindow.loadFile(path.join(__dirname, "token-setup.html"));
  tokenWindow.on("closed", () => {
    tokenWindow = null;
  });
}

ipcMain.handle("setup:save-token", async (event, payload) => {
  if (!tokenWindow || event.sender !== tokenWindow.webContents) {
    return { ok: false, error: "Token setup window is not available." };
  }
  if (!backendContext) return { ok: false, error: "Aria did not start this dashboard." };

  const token = typeof payload?.token === "string" ? payload.token.trim() : "";
  const remember = payload?.remember === true;
  if (!token || token.length > 4096 || /[\r\n]/.test(token)) {
    return { ok: false, error: "Enter a valid token." };
  }

  try {
    await saveTokenConfig(token, remember);
    await stopBackend();
    startBackend(remember ? null : token);
    dashboardUrl = await waitForDashboard();
    if (mainWindow) await mainWindow.loadURL(new URL("/dashboard", dashboardUrl).toString());
    else createWindow();
    if (tokenWindow && !tokenWindow.isDestroyed()) tokenWindow.close();
    return { ok: true };
  } catch (error) {
    return { ok: false, error: error.message || "Could not save the token." };
  }
});

ipcMain.on("setup:cancel", (event) => {
  if (tokenWindow && event.sender === tokenWindow.webContents) tokenWindow.close();
});

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 760,
    minHeight: 560,
    title: "Aria",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (isPublicWebsiteUrl(url)) shell.openExternal(url);
    else openExternalHttps(url);
    return { action: "deny" };
  });
  mainWindow.webContents.on("will-navigate", (event, url) => {
    if (isDashboardUrl(url)) return;
    event.preventDefault();
    if (isPublicWebsiteUrl(url)) shell.openExternal(url);
    else openExternalHttps(url);
  });
  mainWindow.loadURL(new URL("/dashboard", dashboardUrl).toString());
  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

function installMenu() {
  Menu.setApplicationMenu(Menu.buildFromTemplate([
    {
      label: "Aria",
      submenu: [
        {
          label: "Set / Change Token...",
          click: async () => {
            if (!backendProcess || !backendContext) {
              await dialog.showMessageBox({
                type: "info",
                message: "Aria is using a dashboard that was already running.",
                detail: "Start Aria from this app to configure its token here.",
              });
              return;
            }
            createTokenWindow();
          },
        },
        {
          label: "Open Dashboard in Browser",
          click: () => dashboardUrl && shell.openExternal(new URL("/dashboard", dashboardUrl).toString()),
        },
        {
          label: "Open Aria Website",
          click: () => dashboardUrl && shell.openExternal(dashboardUrl),
        },
        { type: "separator" },
        { role: "quit" },
      ],
    },
    { role: "editMenu" },
    { role: "viewMenu" },
    { role: "windowMenu" },
  ]));
}

app.whenReady().then(async () => {
  installMenu();
  try {
    dashboardUrl = await findDashboard();
    if (!dashboardUrl) {
      startBackend();
      await waitForDashboard();
    }
    createWindow();
    if (backendContext && !hasSavedToken()) createTokenWindow();
  } catch (error) {
    dialog.showErrorBox("Aria could not start", error.message);
    app.quit();
  }
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0 && dashboardUrl) createWindow();
});

app.on("before-quit", () => {
  if (backendProcess && backendProcess.exitCode === null) backendProcess.kill();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});