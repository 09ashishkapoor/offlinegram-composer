const state = {
  presets: [],
  activePresetId: null,
  helperText: "Presets are editable in-app and saved to presets.json in this project folder.",
  busy: false,
  fontChoices: [],
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
    exportFormat: "png",
    exportQuality: "92",
    filenameTemplate: "{index}_{preset}_{source_name}",
  },
  batch: {
    imageDir: "",
    quotesFile: null,
    quotesPath: "",
    outputDir: "",
    previews: [],
    importFormat: "text",
    importHeaders: [],
    importRequiredFields: [],
    fieldMapping: {},
    mappingAvailable: false,
    busy: false,
    exportFormat: "png",
    exportQuality: "92",
    filenameTemplate: "{index}_{preset}_{source_name}",
  },
};

const SESSION_STORAGE_KEY = "offlinegram-session-v1";

applySessionState(readSessionState());

const elements = {
  previewEmpty: document.getElementById("preview-empty"),
  previewMeta: document.getElementById("preview-meta"),
  previewImage: document.getElementById("spc-preview-image"),
  presetOptions: document.getElementById("preset-options"),
  presetHelperText: document.getElementById("preset-helper-text"),
  presetLabelInput: document.getElementById("spc-preset-label"),
  presetDescriptionInput: document.getElementById("spc-preset-description"),
  presetEditorMessage: document.getElementById("preset-editor-message"),
  presetCreateButton: document.getElementById("spc-preset-create"),
  presetDuplicateButton: document.getElementById("spc-preset-duplicate"),
  presetSaveMetadataButton: document.getElementById("spc-preset-save-metadata"),
  presetSaveOverlayButton: document.getElementById("spc-preset-save-overlay"),
  presetDeleteButton: document.getElementById("spc-preset-delete"),
  imageUpload: document.getElementById("spc-image-upload"),
  imageSource: document.getElementById("spc-image-source"),
  textLabel: document.getElementById("spc-text-label"),
  textInput: document.getElementById("spc-text"),
  textHelper: document.getElementById("spc-text-helper"),
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
  batchTextDropHint: document.getElementById("batch-text-drop-hint"),
  batchTextHelper: document.getElementById("batch-text-helper"),
  batchStructuredMapping: document.getElementById("batch-structured-mapping"),
  batchFieldMapping: document.getElementById("batch-field-mapping"),
  batchMappingHint: document.getElementById("batch-mapping-hint"),
  batchPreflightMessage: document.getElementById("batch-preflight-message"),
  batchBrowseOutputButton: document.getElementById("batch-browse-output"),
  batchOutputDir: document.getElementById("batch-output-dir"),
  spcExportFormat: document.getElementById("spc-export-format"),
  spcExportQuality: document.getElementById("spc-export-quality"),
  spcExportFilenameTemplate: document.getElementById("spc-export-filename-template"),
  spcExportQualityGroup: document.getElementById("spc-export-quality-group"),
  batchExportFormat: document.getElementById("batch-export-format"),
  batchExportQuality: document.getElementById("batch-export-quality"),
  batchExportFilenameTemplate: document.getElementById("batch-export-filename-template"),
  batchExportQualityGroup: document.getElementById("batch-export-quality-group"),
  batchPreviewButton: document.getElementById("batch-preview"),
  batchExportButton: document.getElementById("batch-export"),
  batchPreviewGrid: document.getElementById("batch-preview-grid"),
  batchMeta: document.getElementById("batch-meta"),
  batchModeGuidance: document.getElementById("batch-mode-guidance"),
  batchModeGuidanceText: document.getElementById("batch-mode-guidance-text"),
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
const DEFAULT_BATCH_GUIDANCE = "Choose a preset to see whether this batch uses one quote per image or structured number/name/caption entries.";
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

function toNumberOrDefault(value, fallback = 0) {
  const parsed = Number.parseFloat(String(value));
  return Number.isFinite(parsed) ? parsed : fallback;
}

function getZoneNumber(zone, field, fallback = 0) {
  return zone && Number.isFinite(Number(zone[field])) ? Number(zone[field]) : fallback;
}

function getFontChoices() {
  return Array.isArray(state.fontChoices) ? state.fontChoices : [];
}

function getFontNameChoices() {
  return getFontChoices().map((font) => String(font?.name || "")).filter(Boolean);
}

function getFirstTextZoneIndex(zones) {
  if (!Array.isArray(zones)) return -1;
  return zones.findIndex((zone) => zone?.type === "text");
}

function renderFontOptions(activeFont) {
  const fontNameChoices = getFontNameChoices();
  const normalizedChoices = [...fontNameChoices, activeFont].filter(Boolean);
  const seen = new Set();
  return normalizedChoices
    .filter((name) => {
      const key = String(name || "").trim();
      if (!key || seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .map((name) => {
      const normalized = String(name || "");
      const isSelected = normalized === activeFont;
      return `<option value="${escapeHtml(normalized)}" ${isSelected ? "selected" : ""}>${escapeHtml(normalized)}</option>`;
    })
    .join("");
}

function getSingleImageTextCopy(mode) {
  if (mode === "structured") {
    return {
      label: "Structured entry",
      helper:
        "This preset splits one entry into number, name, and caption zones. Use <code>1. Name: Caption</code>, or put the number, name, and caption on separate lines.",
      placeholder: "1. Name: Caption\nor:\n1\nName\nCaption",
    };
  }

  return {
    label: "Overlay text",
    helper: "This preset uses one custom text zone. Enter the exact quote or phrase you want on the image.",
    placeholder: "Enter the exact text to place on the image",
  };
}

function getBatchTextCopy(mode) {
  if (mode === "structured") {
    return {
      dropHint: "One structured entry per non-empty line, for example <code>1. Name: Caption</code>. You can also upload CSV/TSV files with headers.",
      helper:
        "Structured mode pairs each image with one entry. Text before <code>.</code> becomes the number, text between <code>.</code> and <code>:</code> becomes the name, and text after <code>:</code> becomes the caption.",
      guidance:
        "Structured mode: each line should use number/name/caption fields (for example, <code>1. Name: Caption</code>).",
      browserHelper: "Navigate to the structured text file and select it.",
      browserFilesHelper: "Choose one UTF-8 .txt, .md, .csv, or .tsv file: plain-text lines or headers for CSV/TSV.",
    };
  }

  if (mode === "quote") {
    return {
      dropHint: "One quote per non-empty line. Each line maps to the preset text zone.",
      helper: "Quote mode pairs each image with one quote line from your file.",
      guidance: "Quote mode: enter one quote per line; each quote is mapped to the custom text zone.",
      browserHelper: "Navigate to the quote file and select it.",
      browserFilesHelper: "Choose one UTF-8 .txt or .md file with one quote per non-empty line.",
    };
  }

  return {
    dropHint: "This preset is not batch-compatible. Choose a different preset to continue.",
    helper:
      "Preset-driven batch mode only works with presets that map either one custom text zone or structured number/name/caption zones.",
    guidance: DEFAULT_BATCH_GUIDANCE,
    browserHelper: "Choose a batch-compatible preset before selecting a text file.",
    browserFilesHelper: "Choose one UTF-8 .txt or .md file after selecting a compatible preset.",
  };
}

function updateSingleImageGuidanceForPreset() {
  const copy = getSingleImageTextCopy(resolveBatchModeFromPreset(state.activePresetId));
  if (elements.textLabel) elements.textLabel.textContent = copy.label;
  if (elements.textHelper) elements.textHelper.innerHTML = copy.helper;
  if (elements.textInput) elements.textInput.placeholder = copy.placeholder;
}

function renderBatchTextModeCopy(mode = resolveBatchModeFromPreset(state.activePresetId)) {
  const copy = getBatchTextCopy(mode);
  if (elements.batchTextDropHint) elements.batchTextDropHint.innerHTML = copy.dropHint;
  if (elements.batchTextHelper) elements.batchTextHelper.innerHTML = copy.helper;
  return copy;
}

function clearBatchPreflightMessage() {
  if (!elements.batchPreflightMessage) return;
  elements.batchPreflightMessage.textContent = "";
  elements.batchPreflightMessage.classList.add("hidden");
  elements.batchPreflightMessage.classList.remove("is-error", "is-info");
}

function setBatchPreflightMessage(message, tone = "error") {
  if (!elements.batchPreflightMessage) return;
  elements.batchPreflightMessage.textContent = message;
  elements.batchPreflightMessage.classList.remove("hidden", "is-error", "is-info");
  elements.batchPreflightMessage.classList.add(tone === "info" ? "is-info" : "is-error");
}

function splitNonEmptyLines(text) {
  return String(text || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function normalizeImportFormat(value) {
  const format = String(value || "").trim().toLowerCase();
  if (format === "tsv") return "tsv";
  if (format === "csv") return "csv";
  return "text";
}

function getFilenameFromState() {
  if (state.batch.quotesFile?.name) return state.batch.quotesFile.name;
  return state.batch.quotesPath || "";
}

function detectImportFormatFromFileOrPath(fileOrPath) {
  const value = String(fileOrPath || "").toLowerCase();
  if (value.endsWith(".csv")) return "csv";
  if (value.endsWith(".tsv")) return "tsv";
  return "text";
}

function getBatchImportFormat() {
  if (state.batch.quotesFile) {
    return detectImportFormatFromFileOrPath(state.batch.quotesFile.name);
  }
  return detectImportFormatFromFileOrPath(state.batch.quotesPath);
}

function getBatchMode() {
  return resolveBatchModeFromPreset(state.activePresetId);
}

function isStructuredCsvOrTsvImport() {
  return getBatchMode() === "structured" && ["csv", "tsv"].includes(state.batch.importFormat);
}

function parseStructuredMappingPayload(payload) {
  if (!payload || typeof payload !== "object") return {};

  const requiredFieldsCandidate =
    payload.required_fields || payload.requiredFields || payload.required || payload.fields_required || payload.requiredFieldsOrdered;
  const requiredFields = Array.isArray(requiredFieldsCandidate)
    ? requiredFieldsCandidate.map((value) => String(value || "").trim()).filter(Boolean)
    : ["number", "name", "caption"];

  const headers = Array.isArray(payload.headers) ? payload.headers.map((value) => String(value || "").trim()) : [];

  const suggested =
    payload.suggested_mapping || payload.suggestedMapping || payload.suggested || payload.field_mapping || payload.fieldMapping || {};
  const suggestedMapping =
    suggested && typeof suggested === "object"
      ? Object.fromEntries(
          Object.entries(suggested).map(([field, column]) => [String(field), String(column || "")]).filter(([, value]) => value),
        )
      : {};

  return {
    requiredFields,
    headers,
    suggestedMapping,
  };
}

function getAvailableRequiredFields() {
  if (state.batch.importRequiredFields?.length) return state.batch.importRequiredFields;
  return ["number", "name", "caption"];
}

function applyDefaultFieldMappingFromHeaders() {
  const headers = state.batch.importHeaders || [];
  const normalizedHeaderByValue = new Map(headers.map((header) => [String(header || "").toLowerCase(), String(header || "")]));
  const defaults = {
    number: normalizedHeaderByValue.get("number") || normalizedHeaderByValue.get("no") || normalizedHeaderByValue.get("#"),
    name: normalizedHeaderByValue.get("name") || normalizedHeaderByValue.get("deity") || normalizedHeaderByValue.get("text"),
    caption: normalizedHeaderByValue.get("caption"),
    title: normalizedHeaderByValue.get("title"),
    subtitle: normalizedHeaderByValue.get("subtitle"),
  };

  const mapping = {};
  const required = getAvailableRequiredFields();
  required.forEach((field) => {
    const suggested = state.batch.fieldMapping && state.batch.fieldMapping[field];
    if (suggested && headers.includes(suggested)) {
      mapping[field] = suggested;
      return;
    }
    if (defaults[field] && headers.includes(defaults[field])) {
      mapping[field] = defaults[field];
    }
  });
  state.batch.fieldMapping = mapping;
  return mapping;
}

function renderBatchFieldMappingPanel() {
  const shouldShow = isStructuredCsvOrTsvImport();
  if (elements.batchStructuredMapping) {
    elements.batchStructuredMapping.classList.toggle("hidden", !shouldShow);
  }

  if (!shouldShow || !elements.batchFieldMapping) {
    if (elements.batchFieldMapping) elements.batchFieldMapping.innerHTML = "";
    return;
  }

  if (!state.batch.importHeaders.length) {
    elements.batchFieldMapping.innerHTML = '<p class="helper-text muted">No headers detected yet. Choose a file path and re-run preflight or preview.</p>';
    return;
  }

  const options = ['<option value="">Auto-detect</option>'].concat(
    state.batch.importHeaders.map(
      (header) => `<option value="${escapeHtml(header)}">${escapeHtml(header)}</option>`,
    ),
  );

  const requiredFields = getAvailableRequiredFields();
  state.batch.fieldMapping = state.batch.fieldMapping || {};
  const selects = requiredFields
    .map((field) => {
      return `
      <div class="inline-row">
        <label class="field-label" for="batch-field-${escapeHtml(field)}">Map <code>${escapeHtml(field)}</code></label>
        <select id="batch-field-${escapeHtml(field)}" data-field="${escapeHtml(field)}">${options.join("")}</select>
      </div>`;
    })
    .join("");

  elements.batchFieldMapping.innerHTML = `<div class="inline-row">${selects}</div>`;

  requiredFields.forEach((field) => {
    const select = document.getElementById(`batch-field-${field}`);
    if (select) {
      select.value = "";
      if (state.batch.fieldMapping[field] && state.batch.importHeaders.includes(state.batch.fieldMapping[field])) {
        select.value = state.batch.fieldMapping[field];
      }
    }
  });
}

function renderBatchMappingHint(message) {
  if (elements.batchMappingHint) {
    elements.batchMappingHint.textContent = message;
  }
}

function isFieldMappingComplete() {
  const required = getAvailableRequiredFields();
  return required.every((field) => Boolean(state.batch.fieldMapping?.[field]));
}

function setBatchFieldMappingFromResponse(payload) {
  const parsed = parseStructuredMappingPayload(payload);
  state.batch.importHeaders = parsed.headers;
  state.batch.importRequiredFields = parsed.requiredFields;
  state.batch.fieldMapping = parsed.suggestedMapping && Object.keys(parsed.suggestedMapping).length
    ? parsed.suggestedMapping
    : applyDefaultFieldMappingFromHeaders();
  renderBatchFieldMappingPanel();
}

function clearBatchImportState() {
  state.batch.importHeaders = [];
  state.batch.importRequiredFields = [];
  state.batch.fieldMapping = {};
  if (elements.batchFieldMapping) {
    elements.batchFieldMapping.innerHTML = "";
  }
  if (elements.batchStructuredMapping) {
    elements.batchStructuredMapping.classList.add("hidden");
  }
}

function looksLikeStructuredLine(line) {
  const trimmed = String(line || "").trim();
  if (!trimmed) return false;
  const dotIndex = trimmed.indexOf(".");
  if (dotIndex <= 0) return false;
  const number = trimmed.slice(0, dotIndex).trim();
  const remainder = trimmed.slice(dotIndex + 1);
  const colonIndex = remainder.indexOf(":");
  if (colonIndex < 0) return false;
  const name = remainder.slice(0, colonIndex).trim();
  const caption = remainder.slice(colonIndex + 1).trim();
  return Boolean(number && name && caption);
}

function analyzeStructuredBatchText(text) {
  const lines = splitNonEmptyLines(text);
  if (!lines.length) return { status: "empty" };
  const invalidLines = lines.filter((line) => !looksLikeStructuredLine(line));
  if (!invalidLines.length) return { status: "valid" };
  return {
    status: invalidLines.length === lines.length ? "likely-quote" : "mixed",
  };
}

async function runBatchPreflight({ includeOutputDir = false } = {}) {
  ensureBatchInputs({ includeOutputDir });

  const mode = await syncBatchPresetDrivenState();
  if (mode === "unknown") {
    const message =
      "This preset is not configured for preset-driven batch mode. Choose a preset with one custom text zone or structured number/name/caption zones, then retry.";
    elements.batchMeta.textContent = message;
    setBatchPreflightMessage(message);
    throw new Error(message);
  }

  if (mode === "structured" && isStructuredCsvOrTsvImport()) {
    if (!isFieldMappingComplete()) {
      const message = "Structured CSV/TSV mode requires each required field to be mapped before preview/export.";
      elements.batchMeta.textContent = message;
      setBatchPreflightMessage(message);
      throw new Error(message);
    }
  }

  if (mode === "structured" && state.batch.quotesFile && state.batch.importFormat === "text") {
    const analysis = analyzeStructuredBatchText(await state.batch.quotesFile.text());
    if (analysis.status === "empty") {
      const message = "The uploaded text file does not contain any usable structured entries. Add one entry per image and retry.";
      elements.batchMeta.textContent = message;
      setBatchPreflightMessage(message);
      throw new Error(message);
    }
    if (analysis.status === "likely-quote") {
      const message =
        "Structured mode is selected, but the uploaded text looks like plain quotes. Use one non-empty line per image in the form 1. Name: Caption, or switch to a single-text preset and retry.";
      elements.batchMeta.textContent = message;
      setBatchPreflightMessage(message);
      throw new Error(message);
    }
    if (analysis.status === "mixed") {
      const message =
        "Structured mode is selected, but some uploaded lines do not follow 1. Name: Caption. Fix those lines or switch to a single-text preset and retry.";
      elements.batchMeta.textContent = message;
      setBatchPreflightMessage(message);
      throw new Error(message);
    }
  }

  return mode;
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

function readSessionState() {
  try {
    const raw = window.localStorage?.getItem(SESSION_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch (error) {
    return {};
  }
}

function persistSessionState() {
  const payload = {
    activePresetId: state.activePresetId,
    text: elements.textInput.value,
    imagePath: state.spc.imagePath || "",
    outputDir: state.spc.outputDir || "",
    batchImageDir: state.batch.imageDir || "",
    batchQuotesPath: state.batch.quotesPath || "",
    batchOutputDir: state.batch.outputDir || "",
    exportFormat: state.spc.exportFormat,
    exportQuality: state.spc.exportQuality,
    filenameTemplate: state.spc.filenameTemplate,
    batchExportFormat: state.batch.exportFormat,
    batchExportQuality: state.batch.exportQuality,
    batchFilenameTemplate: state.batch.filenameTemplate,
  };
  try {
    window.localStorage?.setItem(SESSION_STORAGE_KEY, JSON.stringify(payload));
  } catch (error) {
    // Keep UI usable even when local storage is unavailable.
  }
}

function applySessionState(payload = {}) {
  if (payload.imagePath) state.spc.imagePath = payload.imagePath;
  if (payload.outputDir) state.spc.outputDir = payload.outputDir;
  if (payload.batchImageDir) state.batch.imageDir = payload.batchImageDir;
  if (payload.batchQuotesPath) state.batch.quotesPath = payload.batchQuotesPath;
  if (payload.batchOutputDir) state.batch.outputDir = payload.batchOutputDir;
  if (payload.text) state.spc.text = payload.text;
  if (payload.activePresetId) state.activePresetId = payload.activePresetId;

  if (payload.exportFormat) state.spc.exportFormat = payload.exportFormat;
  if (payload.exportQuality) state.spc.exportQuality = payload.exportQuality;
  if (payload.filenameTemplate) state.spc.filenameTemplate = payload.filenameTemplate;
  if (payload.batchExportFormat) state.batch.exportFormat = payload.batchExportFormat;
  if (payload.batchExportQuality) state.batch.exportQuality = payload.batchExportQuality;
  if (payload.batchFilenameTemplate) state.batch.filenameTemplate = payload.batchFilenameTemplate;
}

function sanitizeExportFormat(value) {
  const normalized = String(value || "").trim().toLowerCase();
  if (normalized === "jpg" || normalized === "jpeg") return "jpg";
  if (normalized === "webp") return "webp";
  return "png";
}

function sanitizeExportQuality(rawValue) {
  const parsed = Number.parseInt(String(rawValue), 10);
  if (!Number.isFinite(parsed)) return "92";
  return String(Math.min(100, Math.max(1, parsed)));
}

function normalizeExportFilenameTemplate(rawValue, fallback) {
  const template = String(rawValue || "").trim();
  return template || fallback;
}

function syncExportControlVisibility() {
  if (elements.spcExportQualityGroup) {
    const isLossy = sanitizeExportFormat(elements.spcExportFormat?.value) !== "png";
    elements.spcExportQualityGroup.classList.toggle("hidden", !isLossy);
  }
  if (elements.batchExportQualityGroup) {
    const isLossy = sanitizeExportFormat(elements.batchExportFormat?.value) !== "png";
    elements.batchExportQualityGroup.classList.toggle("hidden", !isLossy);
  }
}

function updateExportButtonCopy() {
  if (elements.exportButton) {
    const singleFormat = sanitizeExportFormat(state.spc.exportFormat).toUpperCase();
    elements.exportButton.textContent = `Export ${singleFormat}`;
  }
  if (elements.batchExportButton) {
    const batchFormat = sanitizeExportFormat(state.batch.exportFormat).toUpperCase();
    elements.batchExportButton.textContent = `Export batch ${batchFormat}`;
  }
}

function syncExportControlDefaults() {
  if (elements.spcExportFormat) elements.spcExportFormat.value = sanitizeExportFormat(state.spc.exportFormat);
  if (elements.spcExportQuality) elements.spcExportQuality.value = sanitizeExportQuality(state.spc.exportQuality);
  if (elements.spcExportFilenameTemplate)
    elements.spcExportFilenameTemplate.value = normalizeExportFilenameTemplate(state.spc.filenameTemplate, "{index}_{preset}_{source_name}");

  if (elements.batchExportFormat) elements.batchExportFormat.value = sanitizeExportFormat(state.batch.exportFormat);
  if (elements.batchExportQuality) elements.batchExportQuality.value = sanitizeExportQuality(state.batch.exportQuality);
  if (elements.batchExportFilenameTemplate)
    elements.batchExportFilenameTemplate.value = normalizeExportFilenameTemplate(state.batch.filenameTemplate, "{index}_{preset}_{source_name}");

  syncExportControlVisibility();
  updateExportButtonCopy();
}

function updateExportOptionsFromInputs() {
  state.spc.exportFormat = sanitizeExportFormat(elements.spcExportFormat?.value);
  state.spc.exportQuality = sanitizeExportQuality(elements.spcExportQuality?.value);
  state.spc.filenameTemplate = normalizeExportFilenameTemplate(
    elements.spcExportFilenameTemplate?.value,
    "{index}_{preset}_{source_name}",
  );

  state.batch.exportFormat = sanitizeExportFormat(elements.batchExportFormat?.value);
  state.batch.exportQuality = sanitizeExportQuality(elements.batchExportQuality?.value);
  state.batch.filenameTemplate = normalizeExportFilenameTemplate(
    elements.batchExportFilenameTemplate?.value,
    "{index}_{preset}_{source_name}",
  );

  syncExportControlVisibility();
  persistSessionState();
}

function setBatchModeGuidance(mode) {
  if (!elements.batchModeGuidanceText) return;
  const normalizedMode = mode === "structured" ? "structured" : mode === "quote" ? "quote" : null;
  if (!normalizedMode) {
    elements.batchModeGuidanceText.textContent = DEFAULT_BATCH_GUIDANCE;
    return;
  }
  elements.batchModeGuidanceText.innerHTML = getBatchTextCopy(normalizedMode).guidance;
}

function resolveBatchModeFromPreset(presetId) {
  const preset = state.presets.find((item) => item.id === presetId);
  if (!preset || !Array.isArray(preset.zones)) return null;
  const hasStructured = preset.zones.some(
    (zone) => zone.type === "text" && ["number", "name", "caption", "title", "subtitle"].includes(zone.text_source),
  );
  if (hasStructured) return "structured";

  const customTextZones = preset.zones.filter((zone) => zone.type === "text" && zone.text_source === "custom").length;
  if (customTextZones === 1) return "quote";
  return null;
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
  const quotesFile = state.batch.quotesFile?.name || state.batch.quotesPath || "No text file selected";
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

function resetBatchPreview(copy = "Choose a preset, text file, and image folder to build sample previews.") {
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
          ${preview.quote
            ? `<p class="batch-preview-quote">${escapeHtml(preview.quote)}</p>`
            : `
              <p class="batch-preview-quote"><strong>Number:</strong> ${escapeHtml(preview.number || preview.title || "")}</p>
              <p class="batch-preview-quote"><strong>Name:</strong> ${escapeHtml(preview.name || preview.subtitle || "")}</p>
              <p class="batch-preview-quote"><strong>Caption:</strong> ${escapeHtml(preview.caption || "")}</p>
            `}
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
    const batchCopy = getBatchTextCopy(resolveBatchModeFromPreset(state.activePresetId));
    return {
      title: "Choose Batch Text File",
      helper: batchCopy.browserHelper,
      useCurrentFolder: false,
      currentLabel: "Use folder",
      selectedLabel: "Use file",
      filesTitle: "Text Files",
      filesHelper: batchCopy.browserFilesHelper,
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

async function loadFontChoices() {
  try {
    const payload = await fetchJson("/api/fonts");
    const choices = Array.isArray(payload?.fonts) ? payload.fonts : [];
    const names = choices
      .map((font) => ({
        name: String(font?.name || "").trim(),
      }))
      .filter((font) => font.name)
      .sort((a, b) => a.name.localeCompare(b.name));
    state.fontChoices = names;
  } catch (error) {
    state.fontChoices = [];
  }
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
    persistSessionState();
    return;
  }

  if (mode === "output") {
    state.spc.outputDir = path;
    updatePathPills();
    persistSessionState();
    return;
  }

  if (mode === "batch-images") {
    state.batch.imageDir = path;
    updateBatchPathPills();
    clearBatchPreflightMessage();
    resetBatchPreview();
    persistSessionState();
    return;
  }

  if (mode === "batch-quotes") {
    state.batch.quotesPath = path;
    state.batch.quotesFile = null;
    elements.batchQuotesUpload.value = "";
    updateBatchPathPills();
    syncBatchPresetDrivenState({ resetPreview: true }).catch((error) => {
      setBatchPreflightMessage(error?.message || "Unable to inspect structured import file.");
    });
    persistSessionState();
    return;
  }

  if (mode === "batch-output") {
    state.batch.outputDir = path;
    updateBatchPathPills();
    persistSessionState();
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

async function loadPresets(preferredPresetId = null) {
  const payload = await fetchJson("/api/presets");
  state.presets = payload.presets;
  state.helperText = payload.helper_text;

  const preferred = preferredPresetId || state.activePresetId;
  if (preferred && state.presets.some((preset) => preset.id === preferred)) {
    state.activePresetId = preferred;
  } else {
    state.activePresetId = state.presets[0]?.id || null;
  }

  if (elements.textInput.value === "" && state.spc.text) {
    elements.textInput.value = state.spc.text;
  }

  updateSingleImageGuidanceForPreset();
  renderBatchTextModeCopy();
  updateBatchModeGuidanceForPreset();
  elements.presetHelperText.textContent = state.helperText;
  renderPresetOptions();
  renderPresetEditor();
  persistSessionState();
  if (!state.activePresetId) {
    throw new Error("No presets are configured.");
  }
}

function cloneValue(value) {
  return JSON.parse(JSON.stringify(value));
}

function getActivePreset() {
  return state.presets.find((item) => item.id === state.activePresetId) || null;
}

function getFirstEditableTextZone() {
  if (!state.spc.overlayDraft || !state.spc.overlayDraft.length) return null;
  return state.spc.overlayDraft.find((zone) => zone?.type === "text") || null;
}

function syncDraftCustomText(text) {
  if (!Array.isArray(state.spc.overlayDraft)) return;
  state.spc.overlayDraft = state.spc.overlayDraft.map((zone) => {
    if (zone?.type === "text" && zone.text_source === "custom") {
      return { ...zone, custom_text: text };
    }
    return zone;
  });
}

function sanitizeMetadata(value) {
  return String(value || "").trim();
}

function setPresetMessage(message) {
  if (elements.presetEditorMessage) {
    elements.presetEditorMessage.textContent = message;
  }
}

function invalidatePresetDrivenPreviews() {
  resetPreview("Preview appears here.");
  resetBatchPreview("Choose a text file and image folder to build sample previews.");
}

function renderPresetEditor() {
  const preset = getActivePreset();
  const hasPreset = Boolean(preset);
  const draftTextZone = getFirstEditableTextZone();
  const hasImageDraft = Boolean(draftTextZone);

  if (elements.presetLabelInput) {
    elements.presetLabelInput.value = preset?.label || "";
    elements.presetLabelInput.disabled = !hasPreset;
  }
  if (elements.presetDescriptionInput) {
    elements.presetDescriptionInput.value = preset?.description || "";
    elements.presetDescriptionInput.disabled = !hasPreset;
  }

  if (elements.presetSaveMetadataButton) elements.presetSaveMetadataButton.disabled = !hasPreset;
  if (elements.presetSaveOverlayButton) elements.presetSaveOverlayButton.disabled = !hasImageDraft;
  if (elements.presetCreateButton) elements.presetCreateButton.disabled = false;
  if (elements.presetDuplicateButton) elements.presetDuplicateButton.disabled = !hasPreset;

  const canDelete = hasPreset && state.presets.length > 1;
  if (elements.presetDeleteButton) elements.presetDeleteButton.disabled = !canDelete;

  if (!hasPreset) {
    setPresetMessage("No preset loaded. Select one or create a new preset.");
    return;
  }

  if (!hasImageDraft) {
    if (hasPreset) {
      const canEdit = Array.isArray(preset.zones) && preset.zones.some((zone) => zone?.type === "text");
      if (canEdit) {
        setPresetMessage("Open advanced overlay controls and tweak values to save zone edits.");
      } else {
        setPresetMessage("Current preset has no editable text zone to customize.");
      }
    }
    return;
  }

  setPresetMessage(`Preset "${preset.label}" is selected. Save metadata or overlay changes when ready.`);
}

function applyPresetSelection(nextPresetId) {
  if (!nextPresetId) {
    state.activePresetId = state.presets[0]?.id || null;
  } else if (state.presets.some((preset) => preset.id === nextPresetId)) {
    state.activePresetId = nextPresetId;
  }

  invalidatePresetDrivenPreviews();
  updateSingleImageGuidanceForPreset();
  syncBatchPresetDrivenState().catch((error) => {
    setBatchPreflightMessage(error?.message || "Unable to inspect structured import file.");
  });
  renderPresetOptions();
  state.spc.overlayDraft = null;
  if (elements.advancedToggle.open) {
    state.spc.overlayDraft = buildDraftFromSelectedPreset();
    renderAdvancedControls();
  }
  renderPresetEditor();
  persistSessionState();
}

function ensureOverlayDraft() {
  const preset = getActivePreset();
  if (!preset) throw new Error("Choose a preset.");
  if (!state.spc.overlayDraft || !state.spc.overlayDraft.length) {
    throw new Error("No editable overlay draft is available. Open Advanced overlay to load editable values.");
  }
  const textZone = getFirstEditableTextZone();
  if (!textZone) {
    throw new Error("Current preset has no editable text zone.");
  }
}

function presetRequestPayloadFromBody(body) {
  return fetchJson("/api/presets", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

function patchPreset(id, payload) {
  return fetchJson(`/api/presets/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

async function refreshPresetsAfterChange(preferredPresetId) {
  await loadPresets(preferredPresetId);
}

function copyCurrentPresetForCreate() {
  const preset = getActivePreset();
  if (!preset) {
    return {
      label: "New preset",
      description: "",
      zones: [],
    };
  }
  return {
    label: `${preset.label} copy`,
    description: preset.description,
    zones: cloneValue(preset.zones),
  };
}

function buildDuplicatedPresetPayload() {
  const preset = getActivePreset();
  if (!preset) throw new Error("Choose a preset to duplicate.");
  return {
    label: `${preset.label} copy`,
    description: preset.description,
    zones: cloneValue(preset.zones),
  };
}

async function createPresetFromPayload(payload) {
  const response = await presetRequestPayloadFromBody({ preset: payload });
  await refreshPresetsAfterChange(response.preset?.id);
  if (response.preset?.id) {
    state.activePresetId = response.preset.id;
  }
  renderPresetEditor();
  showToast("Preset created.");
}

async function handlePresetCreate() {
  const preset = getActivePreset();
  const source = preset
    ? {
        label: preset.label || "New preset",
        description: preset.description || "",
        zones: cloneValue(preset.zones),
      }
    : {
        label: "New preset",
        description: "",
        zones: cloneValue(state.presets[0]?.zones || []),
      };

  if (!Array.isArray(source.zones) || !source.zones.length) {
    throw new Error("No source preset zones available to create a new preset.");
  }

  source.label = sanitizeMetadata(elements.presetLabelInput?.value) || source.label;
  source.description = sanitizeMetadata(elements.presetDescriptionInput?.value) || source.description;

  const response = await presetRequestPayloadFromBody({ preset: source });
  await refreshPresetsAfterChange(response.preset?.id);
  const createdId = response.preset?.id;
  if (createdId) {
    applyPresetSelection(createdId);
    renderPresetOptions();
  }
  renderPresetEditor();
  showToast("Preset created.");
}

async function handlePresetDuplicate() {
  const response = await presetRequestPayloadFromBody({ preset: buildDuplicatedPresetPayload() });
  await refreshPresetsAfterChange(response.preset?.id);
  const createdId = response.preset?.id;
  if (createdId) {
    applyPresetSelection(createdId);
    renderPresetOptions();
  }
  renderPresetEditor();
  showToast("Preset duplicated.");
}

async function handlePresetSaveMetadata() {
  if (!state.activePresetId) throw new Error("Choose a preset.");
  const label = sanitizeMetadata(elements.presetLabelInput?.value);
  const description = sanitizeMetadata(elements.presetDescriptionInput?.value);
  if (!label || !description) {
    throw new Error("Both label and description are required.");
  }

  await patchPreset(state.activePresetId, {
    label,
    description,
  });

  await refreshPresetsAfterChange(state.activePresetId);
  applyPresetSelection(state.activePresetId);
  showToast("Preset metadata saved.");
}

async function handlePresetSaveOverlay() {
  if (!state.activePresetId) throw new Error("Choose a preset.");
  ensureOverlayDraft();

   const sanitizedZones = cloneValue(state.spc.overlayDraft).map((zone) => {
    if (zone?.type === "text" && zone.text_source === "custom") {
      return { ...zone, custom_text: "" };
    }
    return zone;
  });

  const response = await patchPreset(state.activePresetId, {
    zones: sanitizedZones,
  });
  await refreshPresetsAfterChange(response.preset?.id || state.activePresetId);
  applyPresetSelection(response.preset?.id || state.activePresetId);
  showToast("Preset overlay saved.");
}

async function handlePresetDelete() {
  if (!state.activePresetId) throw new Error("Choose a preset.");
  const deletedId = state.activePresetId;
  const nextId = state.presets.find((preset) => preset.id !== deletedId)?.id || null;
  const response = await fetchJson(`/api/presets/${encodeURIComponent(deletedId)}`, {
    method: "DELETE",
  });

  const preserveId = nextId;
  await refreshPresetsAfterChange(preserveId);
  applyPresetSelection(preserveId);
  setPresetMessage(response.preset?.label ? `Deleted ${response.preset.label}.` : "Preset deleted.");
  showToast("Preset deleted.");
}

function buildDraftFromSelectedPreset() {
  const preset = state.presets.find((item) => item.id === state.activePresetId);
  if (!preset) throw new Error("Choose a preset.");
  const text = elements.textInput.value.trim();
  const draft = cloneValue(Array.isArray(preset.zones) ? preset.zones : []);
  for (let index = 0; index < draft.length; index += 1) {
    const zone = draft[index];
    if (zone?.type === "text" && zone.text_source === "custom") {
      draft[index] = { ...zone, custom_text: text };
    }
  }
  return draft;
}

function renderAdvancedControls() {
  const zone = getFirstEditableTextZone();
  if (!zone) {
    elements.advancedControls.innerHTML = "<p class='helper-text'>The selected preset does not expose a text zone to customize.</p>";
    return;
  }

  const activeFont = String(zone.font_name || "BebasNeue-Regular");
  const fontOptions = renderFontOptions(activeFont);

  elements.advancedControls.innerHTML = `
    <label>Font family
      <select id="advanced-font-name">
        ${fontOptions}
      </select>
    </label>
    <label>Font size
      <input id="advanced-font-size" type="number" min="1" value="${getZoneNumber(zone, "font_size", 64)}">
    </label>
    <label>X position (%)
      <input id="advanced-x-percent" type="number" min="0" max="100" step="0.1" value="${getZoneNumber(zone, "x_percent", 50)}">
    </label>
    <label>Y position (%)
      <input id="advanced-y-percent" type="number" min="0" max="100" step="0.1" value="${getZoneNumber(zone, "y_percent", 50)}">
    </label>
    <label>Alignment
      <select id="advanced-alignment">
        <option value="left" ${zone.alignment === "left" ? "selected" : ""}>Left</option>
        <option value="center" ${zone.alignment === "center" ? "selected" : ""}>Center</option>
        <option value="right" ${zone.alignment === "right" ? "selected" : ""}>Right</option>
      </select>
    </label>
    <label>Max width (%)
      <input id="advanced-max-width-percent" type="number" min="1" max="100" step="0.1" value="${getZoneNumber(zone, "max_width_percent", 86)}">
    </label>
    <label>Text color
      <input id="advanced-text-color" type="color" value="${escapeHtml(zone.text_color || "#ffffff")}"
    >
    </label>
    <label>Text opacity
      <input id="advanced-opacity" type="number" min="0" max="1" step="0.05" value="${getZoneNumber(zone, "opacity", 1)}">
    </label>
    <label class="inline-row">
      <span>Uppercase</span>
      <input id="advanced-uppercase" type="checkbox" ${zone.uppercase ? "checked" : ""}>
    </label>
    <label>Background shape
      <select id="advanced-bg-shape">
        <option value="none" ${zone.bg_shape === "none" ? "selected" : ""}>None</option>
        <option value="rectangle" ${zone.bg_shape === "rectangle" ? "selected" : ""}>Rectangle</option>
        <option value="rounded_rectangle" ${zone.bg_shape === "rounded_rectangle" ? "selected" : ""}>Rounded rectangle</option>
        <option value="full_width_band" ${zone.bg_shape === "full_width_band" ? "selected" : ""}>Full-width band</option>
      </select>
    </label>
    <label>Background color
      <input id="advanced-bg-color" type="color" value="${escapeHtml(zone.bg_color || "#000000")}"
    >
    </label>
    <label>Background opacity
      <input id="advanced-bg-opacity" type="number" min="0" max="1" step="0.05" value="${getZoneNumber(zone, "bg_opacity", 0)}">
    </label>
    <label>Background padding
      <input id="advanced-bg-padding" type="number" min="0" value="${getZoneNumber(zone, "bg_padding", 0)}">
    </label>
    <label class="inline-row">
      <span>Shadow enabled</span>
      <input id="advanced-shadow-enabled" type="checkbox" ${zone.shadow_enabled ? "checked" : ""}>
    </label>
    <label>Shadow X
      <input id="advanced-shadow-dx" type="number" value="${getZoneNumber(zone, "shadow_dx", 0)}">
    </label>
    <label>Shadow Y
      <input id="advanced-shadow-dy" type="number" value="${getZoneNumber(zone, "shadow_dy", 0)}">
    </label>
    <label>Shadow blur
      <input id="advanced-shadow-blur" type="number" min="0" value="${getZoneNumber(zone, "shadow_blur", 0)}">
    </label>
    <label>Shadow color
      <input id="advanced-shadow-color" type="color" value="${escapeHtml(zone.shadow_color || "#000000")}"
    >
    </label>
    <label>Shadow opacity
      <input id="advanced-shadow-opacity" type="number" min="0" max="1" step="0.05" value="${getZoneNumber(zone, "shadow_opacity", 0)}">
    </label>
    <label class="inline-row">
      <span>Outline enabled</span>
      <input id="advanced-outline-enabled" type="checkbox" ${zone.outline_enabled ? "checked" : ""}>
    </label>
    <label>Outline thickness
      <input id="advanced-outline-thickness" type="number" min="0" value="${getZoneNumber(zone, "outline_thickness", 0)}">
    </label>
    <label>Outline color
      <input id="advanced-outline-color" type="color" value="${escapeHtml(zone.outline_color || "#000000")}"
    >
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

  if (includeOutputDir) {
    const exportFormat = sanitizeExportFormat(state.spc.exportFormat);
    data.append("export_format", exportFormat);
    if (exportFormat === "jpg" || exportFormat === "webp") {
      data.append("export_quality", sanitizeExportQuality(state.spc.exportQuality));
    }
    data.append("filename_template", normalizeExportFilenameTemplate(state.spc.filenameTemplate, "{index}_{preset}_{source_name}"));
  }

  return data;
}

function ensureBatchInputs({ includeOutputDir = false } = {}) {
  if (!state.batch.imageDir) {
    throw new Error("Choose an image folder for batch mode.");
  }
  if (!state.batch.quotesFile && !state.batch.quotesPath) {
    throw new Error("Upload or choose a text file first.");
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

  const importFormat = state.batch.importFormat || getBatchImportFormat();
  if (getBatchMode() === "structured" && ["csv", "tsv"].includes(importFormat)) {
    data.append("import_format", importFormat);
    data.append("field_mapping_json", JSON.stringify(state.batch.fieldMapping || {}));
  }

  if (includeOutputDir) {
    data.append("output_dir", state.batch.outputDir);
  } else {
    data.append("sample_count", String(BATCH_PREVIEW_SAMPLE_COUNT));
  }

  if (includeOutputDir) {
    const exportFormat = sanitizeExportFormat(state.batch.exportFormat);
    data.append("export_format", exportFormat);
    if (exportFormat === "jpg" || exportFormat === "webp") {
      data.append("export_quality", sanitizeExportQuality(state.batch.exportQuality));
    }
    data.append("filename_template", normalizeExportFilenameTemplate(state.batch.filenameTemplate, "{index}_{preset}_{source_name}"));
  }

  return data;
}

async function requestBatchImportInspection() {
  clearBatchPreflightMessage();
  if (!state.batch.quotesFile && !state.batch.quotesPath) return;

  const format = state.batch.importFormat || getBatchImportFormat();
  if (!["csv", "tsv"].includes(format)) {
    return;
  }

  const body = new FormData();
  if (state.batch.quotesFile) {
    body.append("text_file", state.batch.quotesFile);
  } else if (state.batch.quotesPath) {
    body.append("text_path", state.batch.quotesPath);
  }
  body.append("import_format", format);
  body.append("preset_id", state.activePresetId || "");

  try {
    const payload = await fetchJson("/api/batch/import/inspect", {
      method: "POST",
      body,
    });
    setBatchFieldMappingFromResponse(payload);
    if (payload?.message) {
      renderBatchMappingHint(String(payload.message));
    }
    return payload;
  } catch (error) {
    if (error?.status === 404 || error?.status === 405) {
      renderBatchMappingHint("Import inspection endpoint unavailable; backend may be using legacy CSV/TSV parsing.");
      state.batch.importHeaders = [];
      state.batch.importRequiredFields = [];
      state.batch.fieldMapping = {};
      renderBatchFieldMappingPanel();
      return;
    }

    const message = error?.message || "Unable to inspect structured import file.";
    setBatchPreflightMessage(message);
    throw error;
  }
}

function describeBatchMode(mode) {
  return mode === "structured" ? "structured mode" : "quote mode";
}

function updateBatchModeGuidanceForPreset() {
  const mode = resolveBatchModeFromPreset(state.activePresetId);
  renderBatchTextModeCopy(mode);
  if (!mode) {
    elements.batchModeGuidanceText.textContent = DEFAULT_BATCH_GUIDANCE;
    if (state.browser.mode === "batch-quotes" && state.browser.data) {
      renderBrowserContents();
    }
    return "unknown";
  }
  setBatchModeGuidance(mode);
  if (state.browser.mode === "batch-quotes" && state.browser.data) {
    renderBrowserContents();
  }
  return mode;
}

async function syncBatchPresetDrivenState({ resetPreview = false, inspectStructuredImport = true } = {}) {
  const mode = updateBatchModeGuidanceForPreset();
  const hasSelectedTextInput = Boolean(state.batch.quotesFile || state.batch.quotesPath);
  state.batch.importFormat = mode === "structured" && hasSelectedTextInput ? getBatchImportFormat() : "text";

  const shouldInspectStructuredImport =
    mode === "structured" && hasSelectedTextInput && ["csv", "tsv"].includes(state.batch.importFormat);

  if (resetPreview) {
    resetBatchPreview();
  }
  clearBatchPreflightMessage();

  if (!shouldInspectStructuredImport) {
    clearBatchImportState();
    renderBatchFieldMappingPanel();
    return mode || "unknown";
  }

  if (!inspectStructuredImport) {
    renderBatchFieldMappingPanel();
    return mode || "unknown";
  }

  await requestBatchImportInspection();
  return mode || "unknown";
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
  const label = sanitizeExportFormat(state.spc.exportFormat).toUpperCase();
  elements.previewMeta.textContent = `Exporting ${label}...`;
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
  await runBatchPreflight();

  setBatchBusy(true);
  elements.batchMeta.textContent = "Rendering sample previews...";
  try {
    const payload = await requestBatchPreview();
    state.batch.previews = payload.previews || [];
    renderBatchPreviewCards();
    const previewCount = state.batch.previews.length;
    setBatchModeGuidance(payload.mode);
    clearBatchPreflightMessage();
    elements.batchMeta.textContent = `Showing ${previewCount} sample preview${previewCount === 1 ? "" : "s"} in ${describeBatchMode(payload.mode)}.`;
  } finally {
    setBatchBusy(false);
  }
}

async function exportBatch() {
  await runBatchPreflight({ includeOutputDir: true });

  setBatchBusy(true);
  const batchFormat = sanitizeExportFormat(state.batch.exportFormat).toUpperCase();
  elements.batchMeta.textContent = `Exporting batch images as ${batchFormat}...`;
  try {
    const payload = await requestBatchGenerate();
    const savedCount = Number(payload.saved_count) || 0;
    setBatchModeGuidance(payload.mode);
    clearBatchPreflightMessage();
    showToast(`Saved ${savedCount} batch image${savedCount === 1 ? "" : "s"}.`);
    elements.batchMeta.textContent = `Saved ${savedCount} file${savedCount === 1 ? "" : "s"} to ${state.batch.outputDir} using ${describeBatchMode(payload.mode)}.`;
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
    persistSessionState();
    updatePathPills();
    resetPreview("Preview appears here.");
  });
}

elements.imageUpload.addEventListener("change", (event) => {
  const [file] = event.target.files || [];
  state.spc.file = file || null;
  state.spc.imagePath = "";
  state.spc.overlayDraft = null;
  persistSessionState();
  updatePathPills();
  resetPreview("Preview appears here.");
});

elements.textInput.addEventListener("input", () => {
  state.spc.text = elements.textInput.value;
  persistSessionState();
  if (elements.advancedToggle.open) {
    if (!state.spc.overlayDraft?.length) {
      state.spc.overlayDraft = buildDraftFromSelectedPreset();
    } else {
      syncDraftCustomText(elements.textInput.value.trim());
    }
    renderAdvancedControls();
  } else {
    state.spc.overlayDraft = null;
  }

  renderPresetEditor();
});

if (elements.spcExportFormat) {
  elements.spcExportFormat.addEventListener("change", () => {
    updateExportOptionsFromInputs();
  });
}

if (elements.spcExportQuality) {
  elements.spcExportQuality.addEventListener("change", () => {
    updateExportOptionsFromInputs();
  });
  elements.spcExportQuality.addEventListener("input", () => {
    updateExportOptionsFromInputs();
  });
}

if (elements.spcExportFilenameTemplate) {
  elements.spcExportFilenameTemplate.addEventListener("change", () => {
    updateExportOptionsFromInputs();
  });
  elements.spcExportFilenameTemplate.addEventListener("input", () => {
    updateExportOptionsFromInputs();
  });
}

if (elements.batchExportFormat) {
  elements.batchExportFormat.addEventListener("change", () => {
    updateExportOptionsFromInputs();
  });
}

if (elements.batchExportQuality) {
  elements.batchExportQuality.addEventListener("change", () => {
    updateExportOptionsFromInputs();
  });
  elements.batchExportQuality.addEventListener("input", () => {
    updateExportOptionsFromInputs();
  });
}

if (elements.batchExportFilenameTemplate) {
  elements.batchExportFilenameTemplate.addEventListener("change", () => {
    updateExportOptionsFromInputs();
  });
  elements.batchExportFilenameTemplate.addEventListener("input", () => {
    updateExportOptionsFromInputs();
  });
}

elements.presetOptions.addEventListener("click", (event) => {
  const button = event.target.closest("[data-preset-id]");
  if (!button) return;
  applyPresetSelection(button.dataset.presetId);
});

elements.presetCreateButton?.addEventListener("click", () => {
  handlePresetCreate().catch((error) => {
    showToast(error.message, true);
    setPresetMessage(error.message);
  });
});

elements.presetDuplicateButton?.addEventListener("click", () => {
  handlePresetDuplicate().catch((error) => {
    showToast(error.message, true);
    setPresetMessage(error.message);
  });
});

elements.presetSaveMetadataButton?.addEventListener("click", () => {
  handlePresetSaveMetadata().catch((error) => {
    showToast(error.message, true);
    setPresetMessage(error.message);
  });
});

elements.presetSaveOverlayButton?.addEventListener("click", () => {
  handlePresetSaveOverlay().catch((error) => {
    showToast(error.message, true);
    setPresetMessage(error.message);
  });
});

elements.presetDeleteButton?.addEventListener("click", () => {
  handlePresetDelete().catch((error) => {
    showToast(error.message, true);
    setPresetMessage(error.message);
  });
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
  syncBatchPresetDrivenState({ resetPreview: true }).catch((error) => {
    setBatchPreflightMessage(error?.message || "Unable to inspect structured import file.");
  });
  persistSessionState();
});

elements.batchPreviewButton.addEventListener("click", () => {
  previewBatch().catch((error) => {
    elements.batchMeta.textContent = error.message;
    setBatchPreflightMessage(error.message);
    showToast(error.message, true);
  });
});

elements.batchFieldMapping?.addEventListener("change", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLSelectElement)) return;
  const field = target.dataset.field;
  if (!field) return;
  const value = target.value;
  if (value) {
    state.batch.fieldMapping[field] = value;
  } else {
    delete state.batch.fieldMapping[field];
  }
});

elements.batchExportButton.addEventListener("click", () => {
  exportBatch().catch((error) => {
    elements.batchMeta.textContent = error.message;
    setBatchPreflightMessage(error.message);
    showToast(error.message, true);
  });
});

if (elements.advancedToggle) {
  elements.advancedToggle.addEventListener("toggle", () => {
    if (!elements.advancedToggle.open) return;
    try {
      state.spc.overlayDraft = buildDraftFromSelectedPreset();
      renderAdvancedControls();
      renderPresetEditor();
    } catch (error) {
      showToast(error.message, true);
    }
  });
}

function applyAdvancedControlChange(event) {
  const zone = getFirstEditableTextZone();
  if (!zone) return;

  const { id, type, checked, value } = event.target;

  switch (id) {
    case "advanced-font-name":
      zone.font_name = value;
      break;
    case "advanced-font-size":
      zone.font_size = toNumberOrDefault(value, zone.font_size);
      break;
    case "advanced-x-percent":
      zone.x_percent = toNumberOrDefault(value, zone.x_percent);
      break;
    case "advanced-y-percent":
      zone.y_percent = toNumberOrDefault(value, zone.y_percent);
      break;
    case "advanced-alignment":
      zone.alignment = value;
      break;
    case "advanced-max-width-percent":
      zone.max_width_percent = toNumberOrDefault(value, zone.max_width_percent);
      break;
    case "advanced-text-color":
      zone.text_color = value;
      break;
    case "advanced-opacity":
      zone.opacity = toNumberOrDefault(value, zone.opacity);
      break;
    case "advanced-uppercase":
      zone.uppercase = type === "checkbox" ? checked : Boolean(value);
      break;
    case "advanced-bg-shape":
      zone.bg_shape = value;
      break;
    case "advanced-bg-color":
      zone.bg_color = value;
      break;
    case "advanced-bg-opacity":
      zone.bg_opacity = toNumberOrDefault(value, zone.bg_opacity);
      break;
    case "advanced-bg-padding":
      zone.bg_padding = toNumberOrDefault(value, zone.bg_padding);
      break;
    case "advanced-shadow-enabled":
      zone.shadow_enabled = type === "checkbox" ? checked : zone.shadow_enabled;
      break;
    case "advanced-shadow-dx":
      zone.shadow_dx = toNumberOrDefault(value, zone.shadow_dx);
      break;
    case "advanced-shadow-dy":
      zone.shadow_dy = toNumberOrDefault(value, zone.shadow_dy);
      break;
    case "advanced-shadow-blur":
      zone.shadow_blur = toNumberOrDefault(value, zone.shadow_blur);
      break;
    case "advanced-shadow-color":
      zone.shadow_color = value;
      break;
    case "advanced-shadow-opacity":
      zone.shadow_opacity = toNumberOrDefault(value, zone.shadow_opacity);
      break;
    case "advanced-outline-enabled":
      zone.outline_enabled = type === "checkbox" ? checked : zone.outline_enabled;
      break;
    case "advanced-outline-thickness":
      zone.outline_thickness = toNumberOrDefault(value, zone.outline_thickness);
      break;
    case "advanced-outline-color":
      zone.outline_color = value;
      break;
    default:
      return;
  }

  renderPresetEditor();
}

elements.advancedControls.addEventListener("input", applyAdvancedControlChange);
elements.advancedControls.addEventListener("change", applyAdvancedControlChange);

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

window.addEventListener("beforeunload", persistSessionState);

wireDragAndDrop();
elements.textInput.value = state.spc.text || "";
syncExportControlDefaults();
updatePathPills();
updateBatchPathPills();
renderBusyState();
resetPreview("Preview appears here.");
resetBatchPreview("Choose a preset, text file, and image folder to build sample previews.");
Promise.all([loadFontChoices(), loadPresets()])
  .catch((error) => showToast(error.message, true));
