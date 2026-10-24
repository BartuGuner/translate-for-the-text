// One shared tooltip element: content rendering and viewport-aware positioning.
import { STRINGS } from "./i18n.js";

const MARGIN = 8;
const GAP = 10;
const MAX_SENSES = 4;
const STAR_PATH = "M12 2.8l2.8 5.8 6.4.9-4.6 4.5 1.1 6.3L12 17.3l-5.7 3 1.1-6.3L2.8 9.5l6.4-.9z";

export class Tooltip {
  constructor(onStar) {
    this.el = document.createElement("div");
    this.el.id = "tooltip";
    this.el.className = "tooltip";
    this.el.setAttribute("role", "tooltip");
    this.el.hidden = true;
    document.body.appendChild(this.el);
    this.anchor = null;
    this.pinned = false;
    this.onStar = onStar;
  }

  get visible() { return !this.el.hidden; }

  show(anchor, info) {
    if (this.anchor && this.anchor !== anchor) this.anchor.removeAttribute("aria-describedby");
    this.anchor = anchor;
    this.render(info);
    this.el.hidden = false;
    anchor.setAttribute("aria-describedby", this.el.id);
    this.position();
  }

  hide() {
    if (this.anchor) this.anchor.removeAttribute("aria-describedby");
    this.anchor = null;
    this.pinned = false;
    this.el.hidden = true;
    this.el.classList.remove("pinned");
  }

  pin() {
    this.pinned = true;
    this.el.classList.add("pinned");
  }

  render({ surface, entry, isProper, isNegative, isSaved }) {
    this.el.replaceChildren();
    const head = el("div", "tt-head");
    head.append(el("div", "tt-word", surface));
    if (entry) head.append(this.starButton(isSaved));
    this.el.append(head);

    if (!entry) {
      this.el.append(el("div", "tt-empty", isProper ? STRINGS.properNoun : STRINGS.noTranslation));
    } else {
      if (entry.lemma !== surface.toLowerCase().replace("\u2019", "'")) {
        this.el.append(el("div", "tt-lemma", `${surface} → ${entry.lemma}`));
      }
      if (isNegative) this.el.append(el("div", "tt-note", STRINGS.negativeNote));
      for (const sense of entry.senses.slice(0, MAX_SENSES)) {
        const row = el("div", "tt-sense");
        row.append(el("span", "tt-pos", STRINGS.pos[sense.pos] || sense.pos), el("span", "tt-tr", sense.tr.join(", ")));
        this.el.append(row);
      }
    }
    this.el.append(el("div", "tt-arrow"));
  }

  starButton(isSaved) {
    const btn = el("button", "tt-star" + (isSaved ? " saved" : ""));
    btn.type = "button";
    btn.id = "tooltip-star";
    btn.setAttribute("aria-label", isSaved ? STRINGS.savedFavorite : STRINGS.saveFavorite);
    btn.setAttribute("aria-pressed", String(isSaved));
    btn.title = btn.getAttribute("aria-label");
    btn.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="${STAR_PATH}"/></svg>`;
    btn.addEventListener("click", (e) => { e.stopPropagation(); this.onStar(); });
    return btn;
  }

  markSaved() {
    const btn = this.el.querySelector(".tt-star");
    if (!btn) return;
    btn.classList.add("saved", "pop");
    btn.setAttribute("aria-pressed", "true");
    btn.setAttribute("aria-label", STRINGS.savedFavorite);
    btn.title = STRINGS.savedFavorite;
  }

  position() {
    const a = this.anchor.getBoundingClientRect();
    const tip = this.el.getBoundingClientRect();
    const vw = document.documentElement.clientWidth;
    const below = a.top - tip.height - GAP < MARGIN && a.bottom + GAP + tip.height <= window.innerHeight - MARGIN;
    const top = below ? a.bottom + GAP : a.top - tip.height - GAP;
    const center = a.left + a.width / 2;
    const left = Math.min(Math.max(center - tip.width / 2, MARGIN), vw - tip.width - MARGIN);
    this.el.style.top = `${top + window.scrollY}px`;
    this.el.style.left = `${left + window.scrollX}px`;
    this.el.classList.toggle("below", below);
    const arrowX = Math.min(Math.max(center - left, 14), tip.width - 14);
    this.el.style.setProperty("--arrow-x", `${arrowX}px`);
  }
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
