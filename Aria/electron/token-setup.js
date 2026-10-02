const form = document.getElementById("token-form");
const tokenInput = document.getElementById("token");
const rememberInput = document.getElementById("remember-token");
const storageNote = document.getElementById("storage-note");
const status = document.getElementById("status");
const submitButton = document.getElementById("submit");

document.getElementById("reveal-token").addEventListener("click", (event) => {
  const reveal = tokenInput.type === "password";
  tokenInput.type = reveal ? "text" : "password";
  event.currentTarget.textContent = reveal ? "Hide" : "Show";
  event.currentTarget.setAttribute("aria-label", reveal ? "Hide token" : "Show token");
});

document.getElementById("cancel").addEventListener("click", () => window.ariaSetup.cancel());
rememberInput.addEventListener("change", () => {
  storageNote.textContent = rememberInput.checked
    ? "Saved encrypted in Aria's local config."
    : "Used only until you close Aria; it will not be saved.";
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const token = tokenInput.value.trim();
  if (!token) {
    status.textContent = "Enter your token to continue.";
    return;
  }

  submitButton.disabled = true;
  status.dataset.state = "pending";
  status.textContent = "Starting Aria...";
  try {
    const result = await window.ariaSetup.saveToken(token, rememberInput.checked);
    if (!result.ok) throw new Error(result.error || "Could not save the token.");
    tokenInput.value = "";
  } catch (error) {
    status.dataset.state = "error";
    status.textContent = error.message;
    submitButton.disabled = false;
  }
});
