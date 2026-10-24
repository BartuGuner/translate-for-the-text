// All user-facing UI strings. To translate the UI, copy this object and change the values.
export const STRINGS = {
  appName: "LexiHover",
  tagline: "Offline English → Turkish reading assistant",
  skipLink: "Skip to content",
  tabReader: "Reader",
  tabFavorites: "Favorites",
  tabSettings: "Settings",

  inputTitle: "Paste a text to read",
  inputHint: "Every word is translated in advance. Hover any word to see its Turkish meaning.",
  inputPlaceholder: "Paste English text here",
  charCount: (n, max) => `${n.toLocaleString("en-US")} / ${max.toLocaleString("en-US")} characters`,
  translate: "Translate",
  clear: "Clear",
  translating: "Translating…",
  edit: "Edit text",
  readerStats: (s) => `${s.words.toLocaleString("en-US")} words · ${s.unique.toLocaleString("en-US")} unique · ${s.not_found.toLocaleString("en-US")} not found`,

  errText_empty: "Please paste some text first.",
  errText_too_long: "The text is too long. The limit is 50,000 characters.",
  errBad_request: "The request could not be processed.",
  errNetwork: "Could not reach the local LexiHover server. Is it still running?",

  noTranslation: "No translation found",
  properNoun: "Proper noun / not in dictionary",
  negativeNote: "negative form (not …)",
  saveFavorite: "Save to favorites",
  savedFavorite: "Saved in favorites",
  pos: { noun: "noun", verb: "verb", adj: "adjective", adv: "adverb", prep: "preposition",
         conj: "conjunction", pron: "pronoun", interj: "interjection", other: "other" },

  favTitle: "Favorites",
  favSearch: "Search favorites",
  favExport: "Export CSV",
  favEmptyTitle: "No favorites yet",
  favEmpty: "Open the Reader, click a word to pin its tooltip, then press the ☆ star to save it here.",
  favNoMatch: "No favorites match your search.",
  favDelete: "Delete",
  favConfirm: "Confirm delete",
  favCount: (n) => `${n} saved word${n === 1 ? "" : "s"}`,

  settingsTitle: "Settings",
  fontSize: "Font size",
  fontSizes: ["Small", "Medium", "Large", "Extra large"],
  theme: "Theme",
  themeLight: "Light",
  themeDark: "Dark",
  highlightUnknown: "Highlight unknown words",
  highlightUnknownHint: "Underline words without a translation with a dotted line.",
  aboutTitle: "About & data sources",
  aboutText: "LexiHover runs entirely on this computer. Your text never leaves it.",
  aboutWiktionary: "Turkish translations from Wiktionary (via kaikki.org / wiktextract), licensed CC BY-SA 4.0.",
  aboutFreedict: "Additional entries from the FreeDict English–Turkish dictionary 0.3, licensed GNU GPL v2 or later.",
  aboutSimplemma: "Lemmatization by simplemma (MIT License).",
};

export function applyStrings(root = document) {
  root.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = STRINGS[el.dataset.i18n]; });
  root.querySelectorAll("[data-i18n-placeholder]").forEach((el) => { el.placeholder = STRINGS[el.dataset.i18nPlaceholder]; });
  root.querySelectorAll("[data-i18n-label]").forEach((el) => { el.setAttribute("aria-label", STRINGS[el.dataset.i18nLabel]); });
}
