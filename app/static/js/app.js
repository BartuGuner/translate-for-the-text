// LexiHover single-page app: input, reader, favorites, settings.
import { STRINGS, applyStrings } from "./i18n.js";
import { Tooltip } from "./tooltip.js";

const MAX_CHARS = 50000;
const CHUNK_THRESHOLD = 5000;   // words; above this, render in chunks
const CHUNK_SEGMENTS = 4000;
const PROGRESS_DELAY = 300;
const HIDE_DELAY = 150;
const FONT_SIZES = [16, 18, 21, 24];
const SETTINGS_KEY = "lexihover.settings";

const $ = (id) => document.getElementById(id);
const state = { doc: null, favorites: [], favLemmas: new Set(), hideTimer: 0, renderToken: 0 };
const settings = loadSettings();
const tooltip = new Tooltip(saveCurrentWord);

// ---------- settings ----------
function loadSettings() {
  const defaults = { fontStep: 1, theme: matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light", highlightUnknown: false };
  try { return { ...defaults, ...JSON.parse(localStorage.getItem(SETTINGS_KEY) || "{}") }; }
  catch { return defaults; }
}

function applySettings() {
  document.documentElement.dataset.theme = settings.theme;
  document.documentElement.style.setProperty("--reader-size", `${FONT_SIZES[settings.fontStep] || 18}px`);
  document.body.classList.toggle("hl-unknown", settings.highlightUnknown);
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  document.querySelectorAll("[data-font-step]").forEach((b) => b.setAttribute("aria-checked", String(Number(b.dataset.fontStep) === settings.fontStep)));
  document.querySelectorAll("[data-theme-choice]").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.themeChoice === settings.theme)));
  $("setting-unknown").checked = settings.highlightUnknown;
}

function buildSettings() {
  const fontGroup = $("font-steps");
  STRINGS.fontSizes.forEach((label, i) => {
    const b = segButton(label, () => { settings.fontStep = i; applySettings(); });
    b.dataset.fontStep = i;
    b.id = `font-step-${i}`;
    b.style.fontSize = `${12 + i * 2}px`;
    fontGroup.append(b);
  });
  const themeGroup = $("theme-choices");
  [["light", STRINGS.themeLight], ["dark", STRINGS.themeDark]].forEach(([value, label]) => {
    const b = segButton(label, () => { settings.theme = value; applySettings(); });
    b.dataset.themeChoice = value;
    b.id = `theme-${value}`;
    themeGroup.append(b);
  });
  $("setting-unknown").addEventListener("change", (e) => { settings.highlightUnknown = e.target.checked; applySettings(); });
}

function segButton(label, onClick) {
  const b = document.createElement("button");
  b.type = "button";
  b.className = "seg";
  b.setAttribute("role", "radio");
  b.textContent = label;
  b.addEventListener("click", onClick);
  return b;
}

// ---------- navigation ----------
function showView(name) {
  tooltip.hide();
  document.querySelectorAll(".view").forEach((v) => { v.hidden = v.dataset.view !== name; });
  document.querySelectorAll(".tab").forEach((t) => t.setAttribute("aria-selected", String(t.dataset.tab === name || (name === "input" && t.dataset.tab === "reader"))));
  if (name === "favorites") loadFavorites();
}

function readerView() { showView(state.doc ? "reader" : "input"); }

// ---------- input ----------
function updateCounter() {
  const n = $("input-text").value.length;
  $("char-count").textContent = STRINGS.charCount(n, MAX_CHARS);
  $("char-count").classList.toggle("over", n > MAX_CHARS);
  $("translate-btn").disabled = n === 0;
}

function showError(msg) {
  $("input-error").textContent = msg;
  $("input-error").hidden = !msg;
}

async function translate() {
  const text = $("input-text").value;
  showError("");
  if (!text.trim()) return showError(STRINGS.errText_empty);
  if (text.length > MAX_CHARS) return showError(STRINGS.errText_too_long);
  const progress = setTimeout(() => document.body.classList.add("busy"), PROGRESS_DELAY);
  $("translate-btn").disabled = true;
  try {
    const res = await fetch("/api/translate", { method: "POST", headers: { "Content-Type": "application/json; charset=utf-8" }, body: JSON.stringify({ text }) });
    const data = await res.json();
    if (!res.ok) return showError(STRINGS[`err${capitalize(data.error)}`] || STRINGS.errBad_request);
    state.doc = data;
    state.text = text;
    await loadFavorites();
    showView("reader");
    renderReader(data);
  } catch {
    showError(STRINGS.errNetwork);
  } finally {
    clearTimeout(progress);
    document.body.classList.remove("busy");
    updateCounter();
  }
}

const capitalize = (s = "") => s.charAt(0).toUpperCase() + s.slice(1);

// ---------- reader ----------
function renderReader(data) {
  const box = $("reader-text");
  box.replaceChildren();
  $("reader-stats").textContent = STRINGS.readerStats(data.stats);
  const token = ++state.renderToken;
  const segs = data.segments;
  if (data.stats.words <= CHUNK_THRESHOLD) {
    box.append(buildFragment(segs, 0, segs.length));
    return;
  }
  let start = 0;
  const step = () => {
    if (token !== state.renderToken) return;
    const end = nextChunkEnd(segs, start);
    box.append(buildFragment(segs, start, end));
    start = end;
    if (start < segs.length) requestAnimationFrame(step);
  };
  step();
}

// Prefer to cut chunks at paragraph breaks.
function nextChunkEnd(segs, start) {
  const limit = Math.min(start + CHUNK_SEGMENTS, segs.length);
  for (let i = limit - 1; i > start + CHUNK_SEGMENTS / 2; i--) {
    if (segs[i].t === "x" && segs[i].s.includes("\n")) return i + 1;
  }
  return limit;
}

function buildFragment(segs, start, end) {
  const frag = document.createDocumentFragment();
  for (let i = start; i < end; i++) {
    const seg = segs[i];
    if (seg.t === "x") { frag.append(seg.s); continue; }
    const span = document.createElement("span");
    span.className = "w";
    span.tabIndex = 0;
    span.textContent = seg.s;
    span.dataset.i = i;
    if (seg.k) {
      const lemma = state.doc.lexicon[seg.k].lemma;
      span.dataset.k = seg.k;
      span.dataset.l = lemma;
      if (state.favLemmas.has(lemma)) span.classList.add("fav");
    } else {
      span.classList.add(seg.pn ? "pn" : "nf");
    }
    frag.append(span);
  }
  return frag;
}

function wordInfo(span) {
  const seg = state.doc.segments[Number(span.dataset.i)];
  const entry = seg.k ? state.doc.lexicon[seg.k] : null;
  return { surface: seg.s, entry, isProper: !!seg.pn, isNegative: !!seg.neg, isSaved: !!entry && state.favLemmas.has(entry.lemma) };
}

function showFor(span) {
  clearTimeout(state.hideTimer);
  if (tooltip.pinned && tooltip.anchor !== span) return;
  if (tooltip.anchor !== span) tooltip.show(span, wordInfo(span));
}

function scheduleHide() {
  clearTimeout(state.hideTimer);
  state.hideTimer = setTimeout(() => { if (!tooltip.pinned) tooltip.hide(); }, HIDE_DELAY);
}

function pin(span) {
  tooltip.hide();
  tooltip.show(span, wordInfo(span));
  tooltip.pin();
}

function bindReader() {
  const box = $("reader-text");
  box.addEventListener("mouseover", (e) => { const w = e.target.closest(".w"); if (w) showFor(w); });
  box.addEventListener("mouseout", (e) => { if (e.target.closest(".w")) scheduleHide(); });
  box.addEventListener("focusin", (e) => { const w = e.target.closest(".w"); if (w) { tooltip.pinned = false; tooltip.show(w, wordInfo(w)); } });
  box.addEventListener("focusout", () => scheduleHide());
  box.addEventListener("click", (e) => { const w = e.target.closest(".w"); if (w) { e.stopPropagation(); pin(w); } });
  box.addEventListener("keydown", (e) => {
    const w = e.target.closest(".w");
    if (w && (e.key === "Enter" || e.key === " ")) {
      e.preventDefault();
      pin(w);
      tooltip.el.querySelector(".tt-star")?.focus();
    }
  });
  tooltip.el.addEventListener("mouseenter", () => clearTimeout(state.hideTimer));
  tooltip.el.addEventListener("mouseleave", scheduleHide);
  tooltip.el.addEventListener("focusout", (e) => { if (!tooltip.el.contains(e.relatedTarget)) scheduleHide(); });
  document.addEventListener("click", (e) => { if (tooltip.visible && !tooltip.el.contains(e.target)) tooltip.hide(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && tooltip.visible) tooltip.hide(); });
  window.addEventListener("resize", () => { if (tooltip.visible) tooltip.position(); });
}

// Sentence around the word at segment `index`, for the favorite's context field.
function contextSentence(index) {
  const segs = state.doc.segments;
  let offset = 0;
  for (let i = 0; i < index; i++) offset += segs[i].s.length;
  const before = state.text.slice(Math.max(0, offset - 300), offset);
  const after = state.text.slice(offset, offset + 300);
  const starts = [...before.matchAll(/[.!?]["'”)]*\s+|\n/g)];
  const last = starts[starts.length - 1];
  const head = last ? before.slice(last.index + last[0].length) : before;
  const end = after.search(/[.!?](?=["'”)]*(\s|$))|\n/);
  const tail = end === -1 ? after : after.slice(0, after[end] === "\n" ? end : end + 1);
  return (head + tail).replace(/\s+/g, " ").trim().slice(0, 300) || null;
}

async function saveCurrentWord() {
  const span = tooltip.anchor;
  if (!span) return;
  const seg = state.doc.segments[Number(span.dataset.i)];
  const entry = state.doc.lexicon[seg.k];
  if (!entry || state.favLemmas.has(entry.lemma)) return;
  const meanings = [...new Set(entry.senses.flatMap((s) => s.tr))].slice(0, 8);
  const body = { word: seg.s, lemma: entry.lemma, pos: entry.senses[0]?.pos || null, meanings, context: contextSentence(Number(span.dataset.i)) };
  const res = await fetch("/api/favorites", { method: "POST", headers: { "Content-Type": "application/json; charset=utf-8" }, body: JSON.stringify(body) });
  if (!res.ok) return;
  state.favLemmas.add(entry.lemma);
  tooltip.markSaved();
  markFavoriteSpans(entry.lemma, true);
}

function markFavoriteSpans(lemma, on) {
  document.querySelectorAll(`#reader-text .w[data-l="${CSS.escape(lemma)}"]`).forEach((s) => s.classList.toggle("fav", on));
}

// ---------- favorites ----------
async function loadFavorites() {
  try {
    const res = await fetch("/api/favorites");
    state.favorites = await res.json();
  } catch {
    state.favorites = [];
  }
  state.favLemmas = new Set(state.favorites.map((f) => f.lemma));
  renderFavorites();
}

function renderFavorites() {
  const q = $("fav-search").value.trim().toLocaleLowerCase("tr");
  const list = $("fav-list");
  const items = state.favorites.filter((f) => !q || [f.word, f.lemma, ...f.meanings].some((s) => s.toLocaleLowerCase("tr").includes(q)));
  $("fav-count").textContent = STRINGS.favCount(state.favorites.length);
  $("fav-empty").hidden = state.favorites.length > 0;
  $("fav-nomatch").hidden = state.favorites.length === 0 || items.length > 0;
  $("fav-tools").hidden = state.favorites.length === 0;
  list.replaceChildren(...items.map(favoriteRow));
}

function favoriteRow(f) {
  const li = document.createElement("li");
  li.className = "fav-row";
  const main = document.createElement("div");
  main.className = "fav-main";
  const head = document.createElement("div");
  head.className = "fav-head";
  head.append(textEl("span", "fav-word", f.word));
  if (f.lemma !== f.word.toLowerCase()) head.append(textEl("span", "fav-lemma", `→ ${f.lemma}`));
  if (f.pos) head.append(textEl("span", "fav-pos", STRINGS.pos[f.pos] || f.pos));
  main.append(head, textEl("div", "fav-tr", f.meanings.join(", ")));
  if (f.context) main.append(textEl("div", "fav-context", f.context));
  const side = document.createElement("div");
  side.className = "fav-side";
  const date = textEl("time", "fav-date", new Date(f.added_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }));
  date.dateTime = f.added_at;
  side.append(date, deleteButton(f));
  li.append(main, side);
  return li;
}

function deleteButton(f) {
  const b = textEl("button", "btn-del", STRINGS.favDelete);
  b.type = "button";
  b.id = `fav-del-${f.id}`;
  let timer = 0;
  b.addEventListener("click", async () => {
    if (!b.classList.contains("confirm")) {
      b.classList.add("confirm");
      b.textContent = STRINGS.favConfirm;
      timer = setTimeout(() => { b.classList.remove("confirm"); b.textContent = STRINGS.favDelete; }, 3000);
      return;
    }
    clearTimeout(timer);
    const res = await fetch(`/api/favorites/${f.id}`, { method: "DELETE" });
    if (res.status !== 204 && res.status !== 404) return;
    state.favorites = state.favorites.filter((x) => x.id !== f.id);
    state.favLemmas.delete(f.lemma);
    markFavoriteSpans(f.lemma, false);
    renderFavorites();
  });
  return b;
}

function textEl(tag, className, text) {
  const n = document.createElement(tag);
  n.className = className;
  n.textContent = text;
  return n;
}

// ---------- init ----------
function init() {
  applyStrings();
  document.title = `${STRINGS.appName} · ${STRINGS.tagline}`;
  buildSettings();
  applySettings();
  bindReader();
  $("input-text").addEventListener("input", updateCounter);
  $("input-text").addEventListener("keydown", (e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) translate(); });
  $("translate-btn").addEventListener("click", translate);
  $("clear-btn").addEventListener("click", () => { $("input-text").value = ""; showError(""); updateCounter(); $("input-text").focus(); });
  $("edit-btn").addEventListener("click", () => { showView("input"); $("input-text").focus(); });
  $("fav-search").addEventListener("input", renderFavorites);
  document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => (t.dataset.tab === "reader" ? readerView() : showView(t.dataset.tab))));
  updateCounter();
  loadFavorites();
  showView("input");
}

init();
