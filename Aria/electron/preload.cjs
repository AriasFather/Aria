const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("ariaSetup", {
  saveToken: (token, remember) => ipcRenderer.invoke("setup:save-token", { token, remember }),
  cancel: () => ipcRenderer.send("setup:cancel"),
});
