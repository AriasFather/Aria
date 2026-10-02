(() => {
  const tabs = Array.from(document.querySelectorAll("[data-doc-tab]"));
  const panels = Array.from(document.querySelectorAll("[data-doc-panel]"));
  const sidebars = Array.from(document.querySelectorAll("[data-doc-sidebar]"));
  const dialog = document.getElementById("docs-search-dialog");
  const searchInput = document.getElementById("docs-search-input");
  const searchResults = document.getElementById("docs-search-results");
  const searchStatus = document.getElementById("docs-search-status");
  const commandFilters = Array.from(document.querySelectorAll("[data-command-filter]"));
  const commandGroups = Array.from(document.querySelectorAll("[data-command-group]"));
  const searchableItems = Array.from(document.querySelectorAll("[data-doc-item]"));
  let activeTab = "guides";

  function selectTab(name) {
    if (!panels.some((panel) => panel.dataset.docPanel === name)) return;
    activeTab = name;
    tabs.forEach((tab) => {
      const selected = tab.dataset.docTab === name;
      tab.setAttribute("aria-selected", String(selected));
      tab.classList.toggle("is-active", selected);
    });
    panels.forEach((panel) => {
      panel.hidden = panel.dataset.docPanel !== name;
    });
    sidebars.forEach((sidebar) => {
      sidebar.hidden = sidebar.dataset.docSidebar !== name;
    });
  }

  function filterCommands(category) {
    commandFilters.forEach((button) => {
      const selected = button.dataset.commandFilter === category;
      button.setAttribute("aria-selected", String(selected));
      button.classList.toggle("is-active", selected);
    });
    commandGroups.forEach((group) => {
      group.hidden = category !== "all" && group.dataset.commandGroup !== category;
    });
  }

  function revealItem(item) {
    const panel = item.closest("[data-doc-panel]");
    if (panel) selectTab(panel.dataset.docPanel);
    const commandGroup = item.closest("[data-command-group]");
    if (commandGroup) filterCommands(commandGroup.dataset.commandGroup);
    requestAnimationFrame(() => item.scrollIntoView({ behavior: "smooth", block: "start" }));
  }

  function resultTitle(item) {
    return item.dataset.docTitle
      || item.querySelector("h2, h3, .docs-command-signature code")?.textContent.trim()
      || "Documentation";
  }

  function resultSummary(item) {
    return item.dataset.docSummary
      || item.querySelector("p:not(.docs-index)")?.textContent.trim()
      || "Open this documentation section.";
  }

  function renderSearchResults() {
    const query = searchInput.value.trim().toLowerCase();
    searchResults.replaceChildren();
    if (!query) {
      searchStatus.textContent = "Search guides, commands, and dashboard topics.";
      return;
    }

    const matches = searchableItems.filter((item) => {
      const content = `${resultTitle(item)} ${resultSummary(item)} ${item.textContent}`.toLowerCase();
      return content.includes(query);
    }).slice(0, 30);

    searchStatus.textContent = matches.length
      ? `${matches.length} result${matches.length === 1 ? "" : "s"}`
      : "No matching documentation found.";

    matches.forEach((item) => {
      const result = document.createElement("button");
      result.type = "button";
      result.className = "docs-search-result";
      result.setAttribute("role", "option");

      const title = document.createElement("strong");
      title.textContent = resultTitle(item);
      const summary = document.createElement("span");
      summary.textContent = resultSummary(item);
      result.append(title, summary);
      result.addEventListener("click", () => {
        dialog.close();
        revealItem(item);
        if (item.id) history.pushState(null, "", `#${encodeURIComponent(item.id)}`);
      });
      searchResults.appendChild(result);
    });
  }

  tabs.forEach((tab) => tab.addEventListener("click", () => selectTab(tab.dataset.docTab)));
  commandFilters.forEach((button) => button.addEventListener("click", () => {
    filterCommands(button.dataset.commandFilter);
  }));

  document.querySelectorAll("[data-doc-link]").forEach((link) => {
    link.addEventListener("click", (event) => {
      const target = document.getElementById(decodeURIComponent(link.hash.slice(1)));
      if (!target) return;
      event.preventDefault();
      selectTab(link.dataset.docTabTarget);
      const commandGroup = target.closest("[data-command-group]");
      if (commandGroup) filterCommands(commandGroup.dataset.commandGroup);
      history.pushState(null, "", link.hash);
      requestAnimationFrame(() => target.scrollIntoView({ behavior: "smooth", block: "start" }));
    });
  });

  document.getElementById("docs-search-open").addEventListener("click", () => {
    dialog.showModal();
    searchInput.focus();
  });
  document.getElementById("docs-search-close").addEventListener("click", () => dialog.close());
  searchInput.addEventListener("input", renderSearchResults);
  dialog.addEventListener("close", () => {
    searchInput.value = "";
    renderSearchResults();
  });

  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      if (!dialog.open) dialog.showModal();
      searchInput.focus();
    }
    if (event.key === "Escape" && dialog.open) dialog.close();
  });

  function revealHashTarget() {
    if (!location.hash) return;
    let targetId;
    try {
      targetId = decodeURIComponent(location.hash.slice(1));
    } catch {
      return;
    }
    const target = document.getElementById(targetId);
    if (!target) return;
    const panel = target.closest("[data-doc-panel]");
    if (panel) selectTab(panel.dataset.docPanel);
    const commandGroup = target.closest("[data-command-group]");
    if (commandGroup) filterCommands(commandGroup.dataset.commandGroup);
    requestAnimationFrame(() => target.scrollIntoView({ block: "start" }));
  }

  window.addEventListener("popstate", revealHashTarget);
  selectTab(activeTab);
  filterCommands("all");
  revealHashTarget();
})();
