/* =========================================================
   DeepDetect — script.js
   Navigation, tabs, media upload, detection, history, and a
   reusable toast utility.
   ========================================================= */

/* ---------- Backend API ----------
   The actual URL lives in config.js (window.DEEPDETECT_API_BASE_URL),
   which is the one file to edit when deploying -- this falls back to
   localhost:5000 if that's somehow missing. There's no client-side
   fallback if the backend itself is unreachable, since silently
   swapping in fake data without saying so would defeat the point of
   labeling mock results honestly.
------------------------------------------------------------*/
const API_BASE_URL = window.DEEPDETECT_API_BASE_URL || "http://localhost:5000";

document.addEventListener("DOMContentLoaded", () => {
  initStickyHeader();
  initMobileNav();
  initActiveNavHighlight();
  initTabs();
  initHistory();
  initMediaUploads();
  preventStrayDrops();
  checkBackendHealth();
});

/* ---------- Sticky header shadow on scroll ---------- */
function initStickyHeader() {
  const header = document.getElementById("siteHeader");
  if (!header) return;

  const onScroll = () => {
    header.classList.toggle("is-scrolled", window.scrollY > 8);
  };
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });
}

/* ---------- Mobile navigation ---------- */
function initMobileNav() {
  const toggle = document.getElementById("navToggle");
  const mobileNav = document.getElementById("mobileNav");
  if (!toggle || !mobileNav) return;

  const closeMenu = () => {
    document.body.classList.remove("nav-open");
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-label", "Open menu");
  };

  const openMenu = () => {
    document.body.classList.add("nav-open");
    toggle.setAttribute("aria-expanded", "true");
    toggle.setAttribute("aria-label", "Close menu");
  };

  toggle.addEventListener("click", () => {
    const isOpen = document.body.classList.contains("nav-open");
    isOpen ? closeMenu() : openMenu();
  });

  // Close the menu whenever a link inside it is used
  mobileNav.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", closeMenu);
  });

  // Close on Escape
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMenu();
  });
}

/* ---------- Highlight the nav link for the section in view ---------- */
function initActiveNavHighlight() {
  const navLinks = document.querySelectorAll("[data-nav]");
  if (!navLinks.length) return;

  const sectionIds = [...navLinks]
    .map((link) => link.getAttribute("href"))
    .filter((href) => href && href.startsWith("#"))
    .map((href) => href.slice(1));

  const sections = sectionIds
    .map((id) => document.getElementById(id))
    .filter(Boolean);

  if (!sections.length) return;

  const setActive = (id) => {
    navLinks.forEach((link) => {
      link.classList.toggle("active", link.getAttribute("href") === `#${id}`);
    });
  };

  const observer = new IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (visible) setActive(visible.target.id);
    },
    { rootMargin: "-40% 0px -55% 0px", threshold: [0, 0.25, 0.5, 1] }
  );

  sections.forEach((section) => observer.observe(section));
}

/* ---------- Detection dashboard tabs (Image / Video) ---------- */
function initTabs() {
  const tabs = document.querySelectorAll(".tab[role='tab']");
  if (!tabs.length) return;

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => activateTab(tab));
    tab.addEventListener("keydown", (event) => {
      const tabList = [...tabs];
      const currentIndex = tabList.indexOf(tab);
      let targetIndex = null;

      if (event.key === "ArrowRight") targetIndex = (currentIndex + 1) % tabList.length;
      if (event.key === "ArrowLeft") targetIndex = (currentIndex - 1 + tabList.length) % tabList.length;

      if (targetIndex !== null) {
        event.preventDefault();
        tabList[targetIndex].focus();
        activateTab(tabList[targetIndex]);
      }
    });
  });

  function activateTab(selectedTab) {
    tabs.forEach((tab) => {
      const isSelected = tab === selectedTab;
      tab.classList.toggle("is-active", isSelected);
      tab.setAttribute("aria-selected", String(isSelected));
      tab.tabIndex = isSelected ? 0 : -1;

      const panel = document.getElementById(tab.getAttribute("aria-controls"));
      if (panel) {
        panel.classList.toggle("is-active", isSelected);
        panel.hidden = !isSelected;
      }
    });
  }
}

/* =========================================================
   STAGE 4: detection history, persisted to localStorage.
   ========================================================= */
const HISTORY_STORAGE_KEY = "deepdetect-history-v1";
const HISTORY_MAX_ENTRIES = 50;

let historyEntries = [];
let historySearchTerm = "";
let historyFilterType = "all";

function initHistory() {
  historyEntries = loadHistoryFromStorage();

  const searchInput = document.getElementById("historySearch");
  searchInput?.addEventListener("input", () => {
    historySearchTerm = searchInput.value.trim().toLowerCase();
    renderHistory();
  });

  document.querySelectorAll(".filter-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".filter-chip").forEach((c) => c.classList.remove("is-active"));
      chip.classList.add("is-active");
      historyFilterType = chip.dataset.filter || "all";
      renderHistory();
    });
  });

  document.getElementById("clearHistoryBtn")?.addEventListener("click", () => {
    if (!historyEntries.length) return;
    if (!confirm("Clear all detection history? This can't be undone.")) return;
    historyEntries = [];
    saveHistoryToStorage();
    renderHistory();
    showToast("Detection history cleared.", "success");
  });

  renderHistory();
}

function loadHistoryFromStorage() {
  try {
    const raw = localStorage.getItem(HISTORY_STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return []; // corrupt or inaccessible storage shouldn't break the page
  }
}

function saveHistoryToStorage() {
  try {
    localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(historyEntries));
  } catch {
    showToast("Couldn't save history — your browser's local storage may be full or disabled.", "error");
  }
}

function addHistoryEntry(entry) {
  historyEntries.unshift(entry);
  if (historyEntries.length > HISTORY_MAX_ENTRIES) historyEntries.length = HISTORY_MAX_ENTRIES;
  saveHistoryToStorage();
  renderHistory();
}

function removeHistoryEntry(id) {
  historyEntries = historyEntries.filter((entry) => entry.id !== id);
  saveHistoryToStorage();
  renderHistory();
}

function getFilteredHistory() {
  return historyEntries.filter((entry) => {
    const matchesType = historyFilterType === "all" || entry.kind === historyFilterType;
    const matchesSearch = !historySearchTerm || entry.fileName.toLowerCase().includes(historySearchTerm);
    return matchesType && matchesSearch;
  });
}

function renderHistory() {
  const table = document.getElementById("historyTable");
  const tbody = document.getElementById("historyTableBody");
  const emptyEl = document.getElementById("historyEmpty");
  const emptyTitle = document.getElementById("historyEmptyTitle");
  const emptySub = document.getElementById("historyEmptySub");
  if (!table || !tbody || !emptyEl) return;

  const filtered = getFilteredHistory();

  if (filtered.length === 0) {
    table.classList.add("is-hidden");
    emptyEl.classList.remove("is-hidden");
    if (historyEntries.length === 0) {
      if (emptyTitle) emptyTitle.textContent = "No detections yet.";
      if (emptySub) emptySub.textContent = "Analyze an image or video above and it will show up here.";
    } else {
      if (emptyTitle) emptyTitle.textContent = "No matching results.";
      if (emptySub) emptySub.textContent = "Try a different search term or filter.";
    }
    tbody.innerHTML = "";
    return;
  }

  table.classList.remove("is-hidden");
  emptyEl.classList.add("is-hidden");
  tbody.innerHTML = "";
  filtered.forEach((entry) => tbody.appendChild(createHistoryRow(entry)));
}

function createHistoryRow(entry) {
  const isDeepfake = entry.prediction === "deepfake";
  const tr = document.createElement("tr");

  const fileCell = document.createElement("td");
  fileCell.className = "history-file-cell";
  fileCell.textContent = entry.fileName;
  fileCell.title = entry.fileName;

  const typeCell = document.createElement("td");
  typeCell.innerHTML = `<svg class="icon icon-sm" aria-hidden="true"><use href="#${entry.kind === "video" ? "icon-video" : "icon-image"}"></use></svg> ${
    entry.kind === "video" ? "Video" : "Image"
  }`;

  const resultCell = document.createElement("td");
  const badge = document.createElement("span");
  badge.className = `history-badge ${isDeepfake ? "is-fake" : "is-real"}`;
  badge.textContent = isDeepfake ? "Deepfake" : "Real";
  resultCell.appendChild(badge);

  const confidenceCell = document.createElement("td");
  confidenceCell.textContent = formatPercent(entry.confidence);

  const dateCell = document.createElement("td");
  dateCell.textContent = formatHistoryDate(entry.timestamp);

  const actionCell = document.createElement("td");
  const removeBtn = document.createElement("button");
  removeBtn.type = "button";
  removeBtn.className = "history-row-remove";
  removeBtn.setAttribute("aria-label", `Remove ${entry.fileName} from history`);
  removeBtn.innerHTML = `<svg class="icon icon-sm" aria-hidden="true"><use href="#icon-close"></use></svg>`;
  removeBtn.addEventListener("click", () => removeHistoryEntry(entry.id));
  actionCell.appendChild(removeBtn);

  tr.append(fileCell, typeCell, resultCell, confidenceCell, dateCell, actionCell);
  return tr;
}

function formatHistoryDate(timestamp) {
  return new Date(timestamp).toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}

function generateId() {
  if (window.crypto?.randomUUID) return crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

/* ---------- Toast utility ----------

/* =========================================================
   STAGE 2: media upload — validation, drag & drop, previews.
   One config-driven implementation shared by the image and
   video panels instead of duplicating the logic twice.
   ========================================================= */

const MEDIA_CONFIG = {
  image: {
    kind: "image",
    dropzone: "dropzoneImage",
    input: "fileInputImage",
    preview: "previewImage",
    previewMedia: "previewImageEl",
    fileName: "imageFileName",
    fileSize: "imageFileSize",
    removeBtn: "removeImageBtn",
    analyzeBtn: "analyzeImageBtn",
    extensions: ["jpg", "jpeg", "png", "webp"],
    mimePrefix: "image/",
    maxBytes: 15 * 1024 * 1024,
    maxLabel: "15 MB",
  },
  video: {
    kind: "video",
    dropzone: "dropzoneVideo",
    input: "fileInputVideo",
    preview: "previewVideo",
    previewMedia: "previewVideoEl",
    fileName: "videoFileName",
    fileSize: "videoFileSize",
    removeBtn: "removeVideoBtn",
    analyzeBtn: "analyzeVideoBtn",
    extensions: ["mp4", "avi", "mov", "mkv"],
    mimePrefix: "video/",
    maxBytes: 100 * 1024 * 1024,
    maxLabel: "100 MB",
  },
};

// Holds the currently selected File (and its preview object URL) per
// media type. Stage 3's mock analysis will read from this directly.
const mediaState = {
  image: { file: null, objectUrl: null },
  video: { file: null, objectUrl: null },
};

function initMediaUploads() {
  Object.values(MEDIA_CONFIG).forEach(wireDropzone);
}

function wireDropzone(config) {
  const dropzone = document.getElementById(config.dropzone);
  const input = document.getElementById(config.input);
  const removeBtn = document.getElementById(config.removeBtn);
  const analyzeBtn = document.getElementById(config.analyzeBtn);
  if (!dropzone || !input) return;

  let dragDepth = 0; // tracks nested dragenter/dragleave so child elements don't cause flicker

  // Clicking anywhere in the dropzone opens the picker, except the
  // "Choose file" label itself (which already does this natively —
  // triggering it twice can open two file dialogs in some browsers).
  dropzone.addEventListener("click", (event) => {
    if (event.target.closest("label, button")) return;
    input.click();
  });

  dropzone.addEventListener("dragenter", (event) => {
    event.preventDefault();
    dragDepth++;
    dropzone.classList.add("is-dragover");
  });

  dropzone.addEventListener("dragover", (event) => {
    event.preventDefault(); // required, or the browser rejects the drop
  });

  dropzone.addEventListener("dragleave", (event) => {
    event.preventDefault();
    dragDepth = Math.max(0, dragDepth - 1);
    if (dragDepth === 0) dropzone.classList.remove("is-dragover");
  });

  dropzone.addEventListener("drop", (event) => {
    event.preventDefault();
    dragDepth = 0;
    dropzone.classList.remove("is-dragover");
    const file = event.dataTransfer?.files?.[0];
    if (file) handleFile(file, config);
  });

  input.addEventListener("change", () => {
    const file = input.files?.[0];
    if (file) handleFile(file, config);
  });

  removeBtn?.addEventListener("click", () => clearFile(config));
  analyzeBtn?.addEventListener("click", () => runAnalysis(config));
}

function handleFile(file, config) {
  const validation = validateFile(file, config);
  if (!validation.valid) {
    showToast(validation.error, "error");
    return;
  }

  const state = mediaState[config.kind];
  if (state.objectUrl) URL.revokeObjectURL(state.objectUrl);

  state.file = file;
  state.objectUrl = URL.createObjectURL(file);

  renderPreview(file, state.objectUrl, config);
  toggleDropzoneState(config, true);
}

function validateFile(file, config) {
  const extension = file.name.split(".").pop().toLowerCase();
  // Some browsers report no MIME type at all for formats like .mkv, so
  // accept on extension OR MIME match rather than requiring both.
  const typeOk = config.extensions.includes(extension) || file.type.startsWith(config.mimePrefix);

  if (!typeOk) {
    return {
      valid: false,
      error: `That file type isn't supported. Accepted: ${config.extensions.join(", ").toUpperCase()}.`,
    };
  }
  if (file.size > config.maxBytes) {
    return {
      valid: false,
      error: `That file is larger than ${config.maxLabel}. Choose a smaller file.`,
    };
  }
  return { valid: true };
}

function renderPreview(file, objectUrl, config) {
  const nameEl = document.getElementById(config.fileName);
  const sizeEl = document.getElementById(config.fileSize);
  const mediaEl = document.getElementById(config.previewMedia);

  if (nameEl) nameEl.textContent = file.name;
  if (mediaEl) mediaEl.src = objectUrl;
  if (sizeEl) sizeEl.textContent = formatBytes(file.size);

  if (config.kind === "video" && mediaEl) {
    mediaEl.addEventListener(
      "loadedmetadata",
      () => {
        if (sizeEl && Number.isFinite(mediaEl.duration)) {
          sizeEl.textContent = `${formatBytes(file.size)} · ${formatDuration(mediaEl.duration)}`;
        }
      },
      { once: true }
    );
  }
}

function toggleDropzoneState(config, hasFile) {
  document.getElementById(config.dropzone)?.classList.toggle("is-hidden", hasFile);
  document.getElementById(config.preview)?.classList.toggle("is-hidden", !hasFile);
  const analyzeBtn = document.getElementById(config.analyzeBtn);
  if (analyzeBtn) analyzeBtn.disabled = !hasFile;
}

function clearFile(config) {
  const state = mediaState[config.kind];
  if (state.objectUrl) URL.revokeObjectURL(state.objectUrl);
  state.file = null;
  state.objectUrl = null;

  const input = document.getElementById(config.input);
  if (input) input.value = ""; // so re-selecting the same file still fires "change"

  const mediaEl = document.getElementById(config.previewMedia);
  mediaEl?.removeAttribute("src");

  toggleDropzoneState(config, false);

  // A stale result/progress panel referring to a file that no longer
  // exists is confusing, so clear those too — they're shared singletons
  // across both tabs, not duplicated per media type.
  document.getElementById("resultCard")?.classList.add("is-hidden");
  document.getElementById("analysisProgress")?.classList.add("is-hidden");
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex++;
  }
  return `${value.toFixed(value < 10 ? 1 : 0)} ${units[unitIndex]}`;
}

function formatDuration(totalSeconds) {
  const rounded = Math.round(totalSeconds);
  const mins = Math.floor(rounded / 60);
  const secs = rounded % 60;
  return `${mins}:${String(secs).padStart(2, "0")}`;
}

/* Without this, dropping a file outside a dropzone makes the browser
   navigate to/open that file, losing the whole page. */
function preventStrayDrops() {
  ["dragover", "drop"].forEach((eventName) => {
    window.addEventListener(eventName, (event) => event.preventDefault());
  });
}

/* =========================================================
   STAGE 3/6: analysis animation, result card, and (as of Stage 6)
   the real backend call that feeds them (see detectMedia() below).
   Every consumer here reads the same response shape regardless of
   where it came from: { prediction, confidence, real_probability,
   deepfake_probability, message }.
   ========================================================= */

const ANALYSIS_STEPS = ["upload", "preprocess", "analyze", "classify", "result"];
const ANALYSIS_STEP_MS = 520;
const ANALYSIS_TOTAL_MS = ANALYSIS_STEPS.length * ANALYSIS_STEP_MS;
const ANALYSIS_STEP_LABELS = {
  upload: "Uploading media…",
  preprocess: "Preprocessing media…",
  analyze: "Running AI analysis…",
  classify: "Classifying result…",
  result: "Finalizing result…",
};

let isAnalyzing = false; // analysis-progress and result-card are shared, single elements — only one run at a time

async function runAnalysis(config) {
  if (isAnalyzing) return;
  const state = mediaState[config.kind];
  if (!state.file) return;

  isAnalyzing = true;
  setAllAnalyzeButtonsDisabled(true);
  setTabsDisabled(true);
  const removeBtn = document.getElementById(config.removeBtn);
  if (removeBtn) removeBtn.disabled = true;

  const progressEl = document.getElementById("analysisProgress");
  const resultEl = document.getElementById("resultCard");
  resultEl.classList.add("is-hidden");
  progressEl.classList.remove("is-hidden");
  resetAnalysisSteps(progressEl);

  const stepsDone = animateSteps(progressEl);

  let data;
  try {
    [data] = await Promise.all([detectMedia(state.file, config.kind), stepsDone]);
  } catch (err) {
    // Fail fast: show the error the moment the request fails rather than
    // waiting out the rest of the cosmetic step animation first.
    progressEl.classList.add("is-hidden");
    showToast(err.message, "error");

    if (removeBtn) removeBtn.disabled = false;
    setTabsDisabled(false);
    Object.values(MEDIA_CONFIG).forEach((c) => {
      const btn = document.getElementById(c.analyzeBtn);
      if (btn) btn.disabled = !mediaState[c.kind].file;
    });
    isAnalyzing = false;
    return;
  }

  progressEl.classList.add("is-hidden");
  renderResult(data);
  resultEl.classList.remove("is-hidden");
  resultEl.scrollIntoView({ behavior: "smooth", block: "nearest" });

  addHistoryEntry({
    id: generateId(),
    fileName: state.file.name,
    kind: config.kind,
    prediction: data.prediction,
    confidence: data.confidence,
    timestamp: Date.now(),
  });

  if (removeBtn) removeBtn.disabled = false;
  setTabsDisabled(false);
  // Re-sync rather than blanket re-enable: only panels that still have
  // a selected file should have a live Analyze button.
  Object.values(MEDIA_CONFIG).forEach((c) => {
    const btn = document.getElementById(c.analyzeBtn);
    if (btn) btn.disabled = !mediaState[c.kind].file;
  });

  isAnalyzing = false;
  showToast("Analysis complete — added to history.", "success");
}

function resetAnalysisSteps(progressEl) {
  progressEl.querySelectorAll(".analysis-steps li").forEach((li) => li.classList.remove("is-current", "is-done"));
  const statusEl = progressEl.querySelector(".analysis-status");
  if (statusEl) statusEl.textContent = "AI is analyzing your media…";
}

function animateSteps(progressEl) {
  const items = [...progressEl.querySelectorAll(".analysis-steps li")];
  const statusEl = progressEl.querySelector(".analysis-status");

  return new Promise((resolve) => {
    let index = 0;
    const advance = () => {
      if (index > 0) items[index - 1].classList.replace("is-current", "is-done");

      if (index < items.length) {
        items[index].classList.add("is-current");
        if (statusEl) statusEl.textContent = ANALYSIS_STEP_LABELS[items[index].dataset.step] || statusEl.textContent;
        index++;
        setTimeout(advance, ANALYSIS_STEP_MS);
      } else {
        resolve();
      }
    };
    advance();
  });
}

function renderResult(data) {
  const resultEl = document.getElementById("resultCard");
  const isDeepfake = data.prediction === "deepfake";

  resultEl.classList.toggle("is-fake", isDeepfake);
  resultEl.classList.toggle("is-real", !isDeepfake);

  document.getElementById("resultIconUse")?.setAttribute("href", isDeepfake ? "#icon-alert" : "#icon-check-circle");
  document.getElementById("resultPrediction").textContent = isDeepfake ? "DEEPFAKE DETECTED" : "REAL MEDIA";
  document.getElementById("resultConfidence").textContent = formatPercent(data.confidence);

  const deepfakePct = formatPercent(data.deepfake_probability);
  const realPct = formatPercent(data.real_probability);
  document.getElementById("barDeepfake").style.width = deepfakePct;
  document.getElementById("deepfakeProb").textContent = deepfakePct;
  document.getElementById("barReal").style.width = realPct;
  document.getElementById("realProb").textContent = realPct;

  document.getElementById("resultSummary").textContent =
    `${data.message} These are classical forensic heuristics (see backend/models/detector.py) — not a trained, validated model. Treat this result as illustrative, not authoritative.`;

  // Stage 4 (done) reads this same `data` object, plus the source file's
  // name/kind and a timestamp, to append a row to detection history.
}

function formatPercent(fraction) {
  return `${(fraction * 100).toFixed(1)}%`;
}

function setAllAnalyzeButtonsDisabled(disabled) {
  Object.values(MEDIA_CONFIG).forEach((c) => {
    const btn = document.getElementById(c.analyzeBtn);
    if (btn) btn.disabled = disabled;
  });
}

function setTabsDisabled(disabled) {
  document.querySelectorAll(".tab[role='tab']").forEach((tab) => {
    tab.disabled = disabled;
  });
}

/* ---------- Backend API call ----------
   Sends the file to the Flask backend (see backend/routes/detection.py)
   and returns its JSON response unchanged. Two distinct failure modes
   are handled with different messages: fetch() itself rejects when the
   server can't be reached at all (not running, wrong port, CORS
   blocked); a non-2xx response means the server responded but rejected
   the request (bad file type, too large) and its own {"error": "..."}
   message is more specific than anything generic we'd write here.
------------------------------------------------------------*/
async function detectMedia(file, kind) {
  const formData = new FormData();
  formData.append("file", file);

  let response;
  try {
    response = await fetch(`${API_BASE_URL}/api/detect/${kind}`, {
      method: "POST",
      body: formData,
    });
  } catch {
    throw new Error(
      `Couldn't reach the detection server at ${API_BASE_URL}. Make sure the backend is running (cd backend && python app.py) and try again.`
    );
  }

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    // Response wasn't JSON (e.g. a proxy error page) — payload stays null,
    // and the generic status-based message below is used instead.
  }

  if (!response.ok) {
    throw new Error((payload && payload.error) || `The server returned an error (status ${response.status}).`);
  }

  return payload;
}

/* One-time, non-blocking check on page load so a missing backend shows
   up as a clear heads-up rather than a confusing failure the first
   time someone clicks Analyze. Never shown on success — a toast every
   page load would just be noise. */
function checkBackendHealth() {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 2500);

  fetch(`${API_BASE_URL}/`, { signal: controller.signal })
    .then((res) => {
      if (!res.ok) throw new Error("bad status");
    })
    .catch(() => {
      showToast(`Detection backend not reachable at ${API_BASE_URL} — start it to run real analyses.`, "error");
    })
    .finally(() => clearTimeout(timeout));
}

/* ---------- Toast utility ----------
   Ready for Stages 2-4 to call, e.g.:
     showToast("That file is larger than 15 MB.", "error");
     showToast("Added to your detection history.", "success");
------------------------------------------------------------*/
function showToast(message, type = "info", duration = 4000) {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast${type === "error" ? " toast-error" : ""}${type === "success" ? " toast-success" : ""}`;
  toast.setAttribute("role", "status");
  toast.textContent = message;

  container.appendChild(toast);
  setTimeout(() => toast.remove(), duration);
}
