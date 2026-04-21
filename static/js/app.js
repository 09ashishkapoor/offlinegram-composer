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
  batch: {
    imageDir: "",
    quotesFile: null,
    quotesPath: "",
    outputDir: "",
    previews: [],
    busy: false,
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
  batchBrowseImagesButton: document.getElementById("batch-browse-images"),
  batchImageDir: document.getElementById("batch-image-dir"),
  batchQuotesUpload: document.getElementById("batch-quotes-upload"),
  batchBrowseQuotesButton: document.getElementById("batch-browse-quotes"),
  batchQuotesFile: document.getElementById("batch-quotes-file"),
  batchBrowseOutputButton: document.getElementById("batch-browse-output"),
  batchOutputDir: document.getElementById("batch-output-dir"),
  batchPreviewButton: document.getElementById("batch-preview"),
  batchExportButton: document.getElementById("batch-export"),
  batchPreviewGrid: document.getElementById("batch-preview-grid"),
  batchMeta: document.getElementById("batch-meta"),
  advancedToggle: document.getElementById("advanced-toggle"),
  advancedControls: document.getElementById("advanced-controls"),
  dropZone: document.getElementById("spc-drop-zone"),
  toast: document.getElementById("toast"),

  browserModal: document.getElementById("browser-modal"),
  browserRoots: document.getElementById("browser-roots"),
  browserFolders: document.getElementById("browser-folders"),
  browserFiles: document.getElementById("browser-files"),
  browserFilesTitle: document.getElementById("browser-files-title"),
  browserFilesHelper: document.getElementById("browser-files-helper"),
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

const BATCH_PREVIEW_SAMPLE_COUNT = 3;
let nativePickerAvailable = null;
let nativePickerFallbackNotified = false;

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
  elements.batchPreviewButton.disabled = state.batch.busy;
  elements.batchExportButton.disabled = state.batch.busy;
}

function setBusy(isBusy) {
  state.busy = isBusy;
  renderBusyState();
}

function setBatchBusy(isBusy) {
  state.batch.busy = isBusy;
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

function updateBatchPathPills() {
  const imageDir = state.batch.imageDir || "No image folder selected";
  const quotesFile = state.batch.quotesFile?.name || state.batch.quotesPath || "No quotes file selected";
  const outputDir = state.batch.outputDir || "No output folder selected";

  elements.batchImageDir.textContent = imageDir;
  elements.batchImageDir.title = imageDir;
  elements.batchQuotesFile.textContent = quotesFile;
  elements.batchQuotesFile.title = quotesFile;
  elements.batchOutputDir.textContent = outputDir;
  elements.batchOutputDir.title = outputDir;
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

function resetBatchPreview(copy = "Choose a quote file and image folder to build sample previews.") {
  state.batch.previews = [];
  elements.batchMeta.textContent = copy;
  elements.batchPreviewGrid.innerHTML = `<div class="muted">${escapeHtml(copy)}</div>`;
}

function renderBatchPreviewCards() {
  if (!state.batch.previews.length) {
    resetBatchPreview();
    return;
  }

  elements.batchPreviewGrid.innerHTML = state.batch.previews
    .map(
      (preview) => `
        <article class="batch-preview-card">
          <img src="data:image/png;base64,${preview.image_b64}" alt="${escapeHtml(preview.filename)} preview">
          <p><strong>${escapeHtml(preview.filename)}</strong></p>
          <p class="batch-preview-quote">${escapeHtml(preview.quote)}</p>
        </article>
      `,
    )
    .join("");
}

function modeConfig(mode) {
  if (mode === "image") {
    return {
      title: "Choose Image",
      helper: "Pick one source image for the composer.",
      useCurrentFolder: false,
      currentLabel: "Use folder",
      selectedLabel: "Use image",
      filesTitle: "Images",
      filesHelper: "Choose one image and confirm it when image selection is active.",
      filesKey: "images",
    };
  }
  if (mode === "batch-quotes") {
    return {
      title: "Choose Batch Quote File",
      helper: "Navigate to the quotes file and select it.",
      useCurrentFolder: false,
      currentLabel: "Use folder",
      selectedLabel: "Use file",
      filesTitle: "Text Files",
      filesHelper: "Choose one UTF-8 .txt or .md file.",
      filesKey: "text_files",
    };
  }
  if (mode === "batch-images") {
    return {
      title: "Choose Batch Image Folder",
      helper: "Navigate to the source image folder and use the current folder.",
      useCurrentFolder: true,
      currentLabel: "Use folder",
      selectedLabel: "Use image",
      filesTitle: "Images",
      filesHelper: "Image files in the current folder.",
      filesKey: "images",
    };
  }
  if (mode === "batch-output") {
    return {
      title: "Choose Batch Output Folder",
      helper: "Navigate to the destination folder and use the current folder.",
      useCurrentFolder: true,
      currentLabel: "Use folder",
      selectedLabel: "Use image",
      filesTitle: "Images",
      filesHelper: "Image files in the current folder.",
      filesKey: "images",
    };
  }
  return {
    title: "Choose Output Folder",
    helper: "Navigate to the destination folder and use the current folder.",
    useCurrentFolder: true,
    currentLabel: "Use folder",
    selectedLabel: "Use image",
    filesTitle: "Images",
    filesHelper: "Image files in the current folder.",
    filesKey: "images",
  };
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) {
    const error = new Error(payload.detail || "Request failed.");
    error.status = response.status;
    throw error;
  }
  return payload;
}

function getInitialPathForMode(mode) {
  if (mode === "image") {
    return state.spc.imagePath || null;
  }
  if (mode === "output") {
    return state.spc.outputDir || null;
  }
  if (mode === "batch-images") {
    return state.batch.imageDir || null;
  }
  if (mode === "batch-quotes") {
    return state.batch.quotesPath || null;
  }
  if (mode === "batch-output") {
    return state.batch.outputDir || null;
  }
  return null;
}

function applySelectedPath(mode, path) {
  if (!path) return;

  if (mode === "image") {
    state.spc.file = null;
    state.spc.imagePath = path;
    elements.imageUpload.value = "";
    state.spc.overlayDraft = null;
    updatePathPills();
    resetPreview("Preview appears here.");
    return;
  }

  if (mode === "output") {
    state.spc.outputDir = path;
    updatePathPills();
    return;
  }

  if (mode === "batch-images") {
    state.batch.imageDir = path;
    updateBatchPathPills();
    resetBatchPreview();
    return;
  }

  if (mode === "batch-quotes") {
    state.batch.quotesPath = path;
    state.batch.quotesFile = null;
    elements.batchQuotesUpload.value = "";
    updateBatchPathPills();
    resetBatchPreview();
    return;
  }

  if (mode === "batch-output") {
    state.batch.outputDir = path;
    updateBatchPathPills();
  }
}

async function requestPathSelection(mode) {
  if (nativePickerAvailable !== false) {
    try {
      const payload = await fetchJson("/api/pick", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode,
          initial_path: getInitialPathForMode(mode),
        }),
      });
      nativePickerAvailable = true;
      if (!payload.cancelled && payload.path) {
        applySelectedPath(mode, payload.path);
      }
      return;
    } catch (error) {
      if (error.status === 501) {
        nativePickerAvailable = false;
        if (!nativePickerFallbackNotified) {
          showToast("Native picker unavailable in this runtime. Using in-app browser.");
          nativePickerFallbackNotified = true;
        }
      } else {
        throw error;
      }
    }
  }

  openBrowser(mode);
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

function ensureBatchInputs({ includeOutputDir = false } = {}) {
  if (!state.batch.imageDir) {
    throw new Error("Choose an image folder for batch mode.");
  }
  if (!state.batch.quotesFile && !state.batch.quotesPath) {
    throw new Error("Upload or choose a quotes file first.");
  }
  if (!state.activePresetId) {
    throw new Error("Choose a preset.");
  }
  if (includeOutputDir && !state.batch.outputDir) {
    throw new Error("Choose an output folder first.");
  }
}

function createBatchFormData(includeOutputDir = false) {
  ensureBatchInputs({ includeOutputDir });

  const data = new FormData();
  if (state.batch.quotesFile) {
    data.append("text_file", state.batch.quotesFile);
  } else if (state.batch.quotesPath) {
    data.append("text_path", state.batch.quotesPath);
  }
  data.append("image_dir", state.batch.imageDir);
  data.append("preset_id", state.activePresetId || "");

  if (includeOutputDir) {
    data.append("output_dir", state.batch.outputDir);
  } else {
    data.append("sample_count", String(BATCH_PREVIEW_SAMPLE_COUNT));
  }

  return data;
}

async function requestBatchPreview() {
  return fetchJson("/api/batch/quotes/preview", {
    method: "POST",
    body: createBatchFormData(false),
  });
}

async function requestBatchGenerate() {
  return fetchJson("/api/batch/quotes/generate", {
    method: "POST",
    body: createBatchFormData(true),
  });
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

async function previewBatch() {
  ensureBatchInputs();

  setBatchBusy(true);
  elements.batchMeta.textContent = "Rendering sample previews...";
  try {
    const payload = await requestBatchPreview();
    state.batch.previews = payload.previews || [];
    renderBatchPreviewCards();
    const previewCount = state.batch.previews.length;
    elements.batchMeta.textContent = `Showing ${previewCount} sample preview${previewCount === 1 ? "" : "s"}.`;
  } finally {
    setBatchBusy(false);
  }
}

async function exportBatch() {
  ensureBatchInputs({ includeOutputDir: true });

  setBatchBusy(true);
  elements.batchMeta.textContent = "Exporting batch images...";
  try {
    const payload = await requestBatchGenerate();
    const savedCount = Number(payload.saved_count) || 0;
    showToast(`Saved ${savedCount} batch image${savedCount === 1 ? "" : "s"}.`);
    elements.batchMeta.textContent = `Saved ${savedCount} file${savedCount === 1 ? "" : "s"} to ${state.batch.outputDir}`;
  } finally {
    setBatchBusy(false);
  }
}

function renderBrowserContents() {
  const data = state.browser.data;
  if (!data) return;

  const cfg = modeConfig(state.browser.mode);
  const filter = state.browser.search.trim().toLowerCase();
  const filePool = Array.isArray(data[cfg.filesKey]) ? data[cfg.filesKey] : [];
  const folders = filter
    ? data.folders.filter((folder) => folder.name.toLowerCase().includes(filter))
    : data.folders;
  const files = filter
    ? filePool.filter((file) => file.name.toLowerCase().includes(filter))
    : filePool;

  elements.browserTitle.textContent = cfg.title;
  elements.browserHelper.textContent = cfg.helper;
  elements.browserFilesTitle.textContent = cfg.filesTitle;
  elements.browserFilesHelper.textContent = cfg.filesHelper;
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

  elements.browserFiles.innerHTML = files.length
    ? files
      .map(
        (file) => `
        <button class="browser-item ${file.path === state.browser.selectedPath ? "is-selected" : ""}" type="button" data-file="${escapeHtml(file.path)}">
          ${escapeHtml(file.name)}
        </button>
      `,
      )
      .join("")
    : `<div class="muted">No files match this filter.</div>`;

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

  document.querySelectorAll("[data-file]").forEach((button) => {
    button.addEventListener("click", () => {
      state.browser.selectedPath = button.dataset.file;
      renderBrowserContents();
    });

    button.addEventListener("dblclick", () => {
      if (!cfg.useCurrentFolder) {
        selectBrowserPath(button.dataset.file);
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
  if (!state.browser.mode) return;
  applySelectedPath(state.browser.mode, path);
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
  resetBatchPreview();
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

elements.browseImageButton.addEventListener("click", () => {
  requestPathSelection("image").catch((error) => showToast(error.message, true));
});
elements.browseOutputButton.addEventListener("click", () => {
  requestPathSelection("output").catch((error) => showToast(error.message, true));
});
elements.batchBrowseImagesButton.addEventListener("click", () => {
  requestPathSelection("batch-images").catch((error) => showToast(error.message, true));
});
elements.batchBrowseQuotesButton.addEventListener("click", () => {
  requestPathSelection("batch-quotes").catch((error) => showToast(error.message, true));
});
elements.batchBrowseOutputButton.addEventListener("click", () => {
  requestPathSelection("batch-output").catch((error) => showToast(error.message, true));
});

elements.batchQuotesUpload.addEventListener("change", (event) => {
  const [file] = event.target.files || [];
  state.batch.quotesFile = file || null;
  state.batch.quotesPath = "";
  updateBatchPathPills();
  resetBatchPreview();
});

elements.batchPreviewButton.addEventListener("click", () => {
  previewBatch().catch((error) => {
    elements.batchMeta.textContent = error.message;
    showToast(error.message, true);
  });
});

elements.batchExportButton.addEventListener("click", () => {
  exportBatch().catch((error) => showToast(error.message, true));
});

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
updateBatchPathPills();
renderBusyState();
resetPreview("Preview appears here.");
resetBatchPreview("Choose a quote file and image folder to build sample previews.");
loadPresets().catch((error) => showToast(error.message, true));
