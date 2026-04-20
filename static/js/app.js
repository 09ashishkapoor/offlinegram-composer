const state = {
  presets: [],
  activePresetId: null,
  helperText: "Edit presets in presets.json (in this project root, next to app.py).",
  busy: false,
  browser: {
    mode: null,
    currentPath: null,
    selectedPath: null,
    search: "",
    data: null,
  },
  spc: {
    file: null,
    imagePath: "",
    text: "",
    outputDir: "",
    preview: "",
    overlayDraft: null,
  },
};

const elements = {
  previewEmpty: document.getElementById("preview-empty"),
  previewMeta: document.getElementById("preview-meta"),
  previewImage: document.getElementById("spc-preview-image"),
  presetOptions: document.getElementById("preset-options"),
  presetHelperText: document.getElementById("preset-helper-text"),
  imageUpload: document.getElementById("spc-image-upload"),
  imageSource: document.getElementById("spc-image-source"),
  textInput: document.getElementById("spc-text"),
  outputPath: document.getElementById("spc-output-path"),
  previewButton: document.getElementById("spc-preview"),
  exportButton: document.getElementById("spc-export"),
  browseImageButton: document.getElementById("spc-browse-image"),
  browseOutputButton: document.getElementById("spc-browse-output"),
  advancedToggle: document.getElementById("advanced-toggle"),
  advancedControls: document.getElementById("advanced-controls"),
  dropZone: document.getElementById("spc-drop-zone"),
  toast: document.getElementById("toast"),

  browserModal: document.getElementById("browser-modal"),
  browserRoots: document.getElementById("browser-roots"),
  browserFolders: document.getElementById("browser-folders"),
  browserImages: document.getElementById("browser-images"),
  browserPath: document.getElementById("browser-path"),
  browserHelper: document.getElementById("browser-helper"),
  browserSearch: document.getElementById("browser-search"),
  browserSelection: document.getElementById("browser-selection"),
  browserSelectCurrent: document.getElementById("browser-select-current"),
  browserUseSelected: document.getElementById("browser-use-selected"),
  browserTitle: document.getElementById("browser-title"),
  browserUp: document.getElementById("browser-up"),
  closeBrowser: document.getElementById("close-browser"),
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function showToast(message, isError = false) {
  elements.toast.textContent = message;
  elements.toast.style.borderColor = isError ? "rgba(214,141,141,0.45)" : "rgba(200,148,98,0.4)";
  elements.toast.classList.remove("hidden");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => {
    elements.toast.classList.add("hidden");
  }, 3500);
}

function renderBusyState() {
  elements.previewButton.disabled = state.busy;
  elements.exportButton.disabled = state.busy;
}

function setBusy(isBusy) {
  state.busy = isBusy;
  renderBusyState();
}

function hasImageSource() {
  return Boolean(state.spc.file || state.spc.imagePath);
}

function updatePathPills() {
  const source = state.spc.file?.name || state.spc.imagePath || "No image selected";
  const output = state.spc.outputDir || "No output folder selected";
  elements.imageSource.textContent = source;
  elements.imageSource.title = source;
  elements.outputPath.textContent = output;
  elements.outputPath.title = output;
}

function resetPreview(copy = "Preview appears here.") {
  state.spc.preview = "";
  elements.previewEmpty.textContent = copy;
  elements.previewEmpty.classList.remove("hidden");
  elements.previewImage.classList.add("hidden");
  elements.previewImage.removeAttribute("src");
  elements.previewMeta.textContent = "Choose an image and preset to preview.";
}

function setPreview(base64, meta = "Preview ready.") {
  state.spc.preview = base64;
  elements.previewImage.src = `data:image/png;base64,${base64}`;
  elements.previewImage.classList.remove("hidden");
  elements.previewEmpty.classList.add("hidden");
  elements.previewMeta.textContent = meta;
}

function modeConfig(mode) {
  if (mode === "image") {
    return {
      title: "Choose Image",
      helper: "Pick one source image for the composer.",
      useCurrentFolder: false,
      currentLabel: "Use folder",
      selectedLabel: "Use image",
    };
  }
  return {
    title: "Choose Output Folder",
    helper: "Navigate to the destination folder and use the current folder.",
    useCurrentFolder: true,
    currentLabel: "Use folder",
    selectedLabel: "Use image",
  };
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "Request failed.");
  }
  return payload;
}

function renderPresetOptions() {
  elements.presetOptions.innerHTML = state.presets
    .map(
      (preset) => `
        <button
          type="button"
          class="preset-card ${preset.id === state.activePresetId ? "active" : ""}"
          data-preset-id="${escapeHtml(preset.id)}"
        >
          <strong>${escapeHtml(preset.label)}</strong>
          <p>${escapeHtml(preset.description)}</p>
        </button>
      `,
    )
    .join("");
}

async function loadPresets() {
  const payload = await fetchJson("/api/presets");
  state.presets = payload.presets;
  state.helperText = payload.helper_text;
  state.activePresetId = state.presets[0]?.id || null;
  elements.presetHelperText.textContent = state.helperText;
  renderPresetOptions();
  if (!state.activePresetId) {
    throw new Error("No presets are configured.");
  }
}

function cloneValue(value) {
  return JSON.parse(JSON.stringify(value));
}

function buildDraftFromSelectedPreset() {
  const preset = state.presets.find((item) => item.id === state.activePresetId);
  if (!preset) throw new Error("Choose a preset.");
  const text = elements.textInput.value.trim();
  return cloneValue(preset.zones).map((zone) => {
    if (zone.type === "text" && zone.text_source === "custom") {
      return { ...zone, custom_text: text };
    }
    return zone;
  });
}

function renderAdvancedControls() {
  const zone = state.spc.overlayDraft?.find((item) => item.type === "text");
  if (!zone) {
    elements.advancedControls.innerHTML = "<p class='helper-text'>Choose a preset to customize.</p>";
    return;
  }

  elements.advancedControls.innerHTML = `
    <label>Font size <input id="advanced-font-size" type="number" value="${Number(zone.font_size) || 64}"></label>
    <label>Y position <input id="advanced-y-percent" type="number" value="${Number(zone.y_percent) || 50}"></label>
    <label>Outline weight <input id="advanced-outline" type="number" value="${Number(zone.outline_thickness) || 8}"></label>
    <label>Background shape
      <select id="advanced-bg-shape">
        <option value="none" ${zone.bg_shape === "none" ? "selected" : ""}>None</option>
        <option value="rectangle" ${zone.bg_shape === "rectangle" ? "selected" : ""}>Rectangle</option>
      </select>
    </label>
  `;
}

function createSingleImageFormData(includeOutputDir = false) {
  const data = new FormData();

  if (state.spc.file) {
    data.append("image", state.spc.file);
  } else if (state.spc.imagePath) {
    data.append("image_path", state.spc.imagePath);
  }

  data.append("preset_id", state.activePresetId || "");
  data.append("text", elements.textInput.value.trim());

  if (state.spc.overlayDraft) {
    data.append("overlay_json", JSON.stringify(state.spc.overlayDraft));
  }

  if (includeOutputDir) {
    data.append("output_dir", state.spc.outputDir);
  }

  return data;
}

async function previewCurrent() {
  if (!hasImageSource()) {
    throw new Error("Choose an image first.");
  }

  setBusy(true);
  elements.previewMeta.textContent = "Rendering preview...";
  try {
    const payload = await fetchJson("/api/preview", {
      method: "POST",
      body: createSingleImageFormData(false),
    });
    setPreview(payload.image_b64, "Preview ready.");
  } finally {
    setBusy(false);
  }
}

async function exportCurrent() {
  if (!hasImageSource()) {
    throw new Error("Choose an image first.");
  }
  if (!state.spc.outputDir) {
    throw new Error("Choose an output folder first.");
  }

  setBusy(true);
  elements.previewMeta.textContent = "Exporting PNG...";
  try {
    const payload = await fetchJson("/api/generate", {
      method: "POST",
      body: createSingleImageFormData(true),
    });
    showToast(`Saved ${payload.filename}`);
    elements.previewMeta.textContent = `Saved to ${payload.saved_to}`;
  } finally {
    setBusy(false);
  }
}

function renderBrowserContents() {
  const data = state.browser.data;
  if (!data) return;

  const cfg = modeConfig(state.browser.mode);
  const filter = state.browser.search.trim().toLowerCase();
  const folders = filter
    ? data.folders.filter((folder) => folder.name.toLowerCase().includes(filter))
    : data.folders;
  const images = filter
    ? data.images.filter((image) => image.name.toLowerCase().includes(filter))
    : data.images;

  elements.browserTitle.textContent = cfg.title;
  elements.browserHelper.textContent = cfg.helper;
  elements.browserPath.textContent = data.current || "Select a drive to begin.";
  elements.browserSelection.textContent = state.browser.selectedPath || "Nothing selected yet";

  elements.browserRoots.innerHTML = data.roots
    .map((root) => `<button class="ghost-button" type="button" data-root="${escapeHtml(root)}">${escapeHtml(root)}</button>`)
    .join("");

  elements.browserFolders.innerHTML = folders.length
    ? folders
      .map((folder) => `<button class="browser-item" type="button" data-folder="${escapeHtml(folder.path)}">${escapeHtml(folder.name)}</button>`)
      .join("")
    : `<div class="muted">No folders match this filter.</div>`;

  elements.browserImages.innerHTML = images.length
    ? images
      .map(
        (image) => `
        <button class="browser-item ${image.path === state.browser.selectedPath ? "is-selected" : ""}" type="button" data-image="${escapeHtml(image.path)}">
          ${escapeHtml(image.name)}
        </button>
      `,
      )
      .join("")
    : `<div class="muted">No images match this filter.</div>`;

  elements.browserSelectCurrent.classList.toggle("hidden", !cfg.useCurrentFolder);
  elements.browserUseSelected.classList.toggle("hidden", cfg.useCurrentFolder);
  elements.browserSelectCurrent.textContent = cfg.currentLabel;
  elements.browserUseSelected.textContent = cfg.selectedLabel;
  elements.browserSelectCurrent.disabled = !(cfg.useCurrentFolder && data.current);
  elements.browserUseSelected.disabled = !(state.browser.selectedPath && !cfg.useCurrentFolder);

  document.querySelectorAll("[data-root]").forEach((button) => {
    button.addEventListener("click", () => browse(button.dataset.root));
  });

  document.querySelectorAll("[data-folder]").forEach((button) => {
    button.addEventListener("click", () => browse(button.dataset.folder));
  });

  document.querySelectorAll("[data-image]").forEach((button) => {
    button.addEventListener("click", () => {
      state.browser.selectedPath = button.dataset.image;
      renderBrowserContents();
    });

    button.addEventListener("dblclick", () => {
      if (state.browser.mode === "image") {
        selectBrowserPath(button.dataset.image);
      }
    });
  });

  elements.browserUp.disabled = !data.parent;
}

async function browse(path = null) {
  const query = path ? `?path=${encodeURIComponent(path)}` : "";
  elements.browserPath.textContent = "Loading...";
  state.browser.selectedPath = null;
  state.browser.data = await fetchJson(`/api/browse${query}`);
  state.browser.currentPath = state.browser.data.current;
  renderBrowserContents();
}

function closeBrowser() {
  elements.browserModal.classList.add("hidden");
  state.browser.mode = null;
  state.browser.selectedPath = null;
  state.browser.search = "";
  state.browser.data = null;
  elements.browserSearch.value = "";
}

function openBrowser(mode) {
  state.browser.mode = mode;
  state.browser.selectedPath = null;
  state.browser.search = "";
  state.browser.data = null;
  elements.browserModal.classList.remove("hidden");
  browse().catch((error) => {
    showToast(error.message, true);
    elements.browserPath.textContent = "Unable to browse folders.";
  });
}

function selectBrowserPath(path) {
  if (state.browser.mode === "image") {
    state.spc.file = null;
    state.spc.imagePath = path;
    elements.imageUpload.value = "";
    resetPreview("Preview appears here.");
  }

  if (state.browser.mode === "output") {
    state.spc.outputDir = path;
  }

  updatePathPills();
  closeBrowser();
}

function wireDragAndDrop() {
  ["dragenter", "dragover"].forEach((eventName) => {
    elements.dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      elements.dropZone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    elements.dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      elements.dropZone.classList.remove("dragover");
    });
  });

  elements.dropZone.addEventListener("drop", (event) => {
    const [file] = event.dataTransfer.files || [];
    if (!file) return;
    state.spc.file = file;
    state.spc.imagePath = "";
    elements.imageUpload.files = event.dataTransfer.files;
    state.spc.overlayDraft = null;
    updatePathPills();
    resetPreview("Preview appears here.");
  });
}

elements.imageUpload.addEventListener("change", (event) => {
  const [file] = event.target.files || [];
  state.spc.file = file || null;
  state.spc.imagePath = "";
  state.spc.overlayDraft = null;
  updatePathPills();
  resetPreview("Preview appears here.");
});

elements.textInput.addEventListener("input", () => {
  state.spc.text = elements.textInput.value;
  state.spc.overlayDraft = null;
  if (elements.advancedToggle.open) {
    state.spc.overlayDraft = buildDraftFromSelectedPreset();
    renderAdvancedControls();
  }
});

elements.presetOptions.addEventListener("click", (event) => {
  const button = event.target.closest("[data-preset-id]");
  if (!button) return;
  state.activePresetId = button.dataset.presetId;
  state.spc.overlayDraft = null;
  renderPresetOptions();
  if (elements.advancedToggle.open) {
    state.spc.overlayDraft = buildDraftFromSelectedPreset();
    renderAdvancedControls();
  }
});

elements.previewButton.addEventListener("click", () => {
  previewCurrent().catch((error) => showToast(error.message, true));
});

elements.exportButton.addEventListener("click", () => {
  exportCurrent().catch((error) => showToast(error.message, true));
});

elements.browseImageButton.addEventListener("click", () => openBrowser("image"));
elements.browseOutputButton.addEventListener("click", () => openBrowser("output"));

if (elements.advancedToggle) {
  elements.advancedToggle.addEventListener("toggle", () => {
    if (!elements.advancedToggle.open) return;
    try {
      state.spc.overlayDraft = buildDraftFromSelectedPreset();
      renderAdvancedControls();
    } catch (error) {
      showToast(error.message, true);
    }
  });
}

elements.advancedControls.addEventListener("input", (event) => {
  const zone = state.spc.overlayDraft?.find((item) => item.type === "text");
  if (!zone) return;
  if (event.target.id === "advanced-font-size") zone.font_size = Number(event.target.value);
  if (event.target.id === "advanced-y-percent") zone.y_percent = Number(event.target.value);
  if (event.target.id === "advanced-outline") zone.outline_thickness = Number(event.target.value);
  if (event.target.id === "advanced-bg-shape") zone.bg_shape = event.target.value;
});

elements.advancedControls.addEventListener("change", (event) => {
  const zone = state.spc.overlayDraft?.find((item) => item.type === "text");
  if (!zone) return;
  if (event.target.id === "advanced-bg-shape") zone.bg_shape = event.target.value;
});

elements.closeBrowser.addEventListener("click", closeBrowser);

elements.browserModal.addEventListener("click", (event) => {
  if (event.target === elements.browserModal) closeBrowser();
});

elements.browserSearch.addEventListener("input", () => {
  state.browser.search = elements.browserSearch.value;
  renderBrowserContents();
});

elements.browserUp.addEventListener("click", () => {
  const parent = state.browser.data?.parent;
  if (parent) {
    browse(parent).catch((error) => showToast(error.message, true));
  }
});

elements.browserSelectCurrent.addEventListener("click", () => {
  if (state.browser.currentPath) {
    selectBrowserPath(state.browser.currentPath);
  }
});

elements.browserUseSelected.addEventListener("click", () => {
  if (state.browser.selectedPath) {
    selectBrowserPath(state.browser.selectedPath);
  }
});

wireDragAndDrop();
updatePathPills();
renderBusyState();
resetPreview("Preview appears here.");
loadPresets().catch((error) => showToast(error.message, true));
