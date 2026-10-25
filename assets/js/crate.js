/* crate.js: draws the crate from data/v1/releases (title, date, type, artwork, slug). No play numbers are read or needed.
   Also fills the "New transmission" strip from data/v1/pulse.json (title + date only, never a number). */
const hash = (s) => { let h = 2166136261; for (const c of s) h = Math.imul(h ^ c.charCodeAt(0), 16777619); return h >>> 0; };
const rnd = (h, n) => ((h >>> (n * 5)) & 31) / 31;
/* A sleeve for tracks with no cover art: one ink mark on paper, the same every time for the same title. Labelled honestly. */
export function sleeve(r) {
  const h = hash(r.title + r.date), y = 18 + rnd(h, 0) * 64, x = 30 + rnd(h, 1) * 40, rad = 6 + rnd(h, 2) * 20;
  return `<svg viewBox="0 0 100 100" role="img" aria-label="Generated sleeve for ${r.title.replace(/"/g, "'")}"><rect width="100" height="100" fill="#efede8"/>` +
    `<line x1="0" x2="100" y1="${y.toFixed(1)}" y2="${y.toFixed(1)}" stroke="#22211f" stroke-width=".6"/>` +
    `<circle cx="${x.toFixed(1)}" cy="${(y + rad + 6).toFixed(1)}" r="${rad.toFixed(1)}" fill="${rnd(h, 3) > .5 ? "#22211f" : "none"}" stroke="#22211f" stroke-width=".6"/>` +
    `<text x="6" y="94" font-family="ui-monospace,monospace" font-size="5" fill="#22211f">${r.date.slice(0, 4)}</text></svg>`;
}
const root = document.querySelector("[data-crate]");
if (root) fetch("/data/v1/releases.json").then((r) => r.json()).then(({ discography }) => {
  const list = [...discography].sort((a, b) => a.date.localeCompare(b.date));
  const ul = root.querySelector(".crate-spines"), card = root.querySelector(".crate-card"), stage = root.querySelector(".crate-stage");
  ul.innerHTML = list.map((r, i) => `<li><a href="/releases/${r.slug}.html" data-i="${i}" data-kind="${r.type}" aria-label="${r.title}, ${r.date.slice(0, 4)}"></a></li>`).join("");
  const show = (a) => {
    const r = list[a.dataset.i], b = a.getBoundingClientRect(), s = stage.getBoundingClientRect();
    card.innerHTML = (r.artwork ? `<img src="${r.artwork}" width="220" height="220" alt="Cover of ${r.title.replace(/"/g, "'")}">` : sleeve(r)) +
      `<p>${r.title}<small>${r.date}${r.artwork ? (r.artwork_page ? " · Cover from Apple Music" : "") : " · generated sleeve, no cover on file"}</small></p>`;
    card.style.translate = `${Math.max(0, Math.min(s.width - card.offsetWidth, b.left - s.left - card.offsetWidth / 2))}px 0`;
  };
  ul.addEventListener("pointerover", (e) => e.target.closest("a") && show(e.target.closest("a")));
  ul.addEventListener("focusin", (e) => show(e.target));
  ul.scrollLeft = ul.scrollWidth; show(ul.lastElementChild.firstElementChild);
  const years = root.querySelector(".crate-years"); years.innerHTML = `<span>${list[0].date.slice(0, 4)}</span><span>${list.at(-1).date.slice(0, 4)}</span>`;
});

/* New transmission strip: the newest heartbeat change, words and a date only. */
const strip = document.querySelector("[data-transmission]");
if (strip) fetch("/data/v1/pulse.json").then((r) => r.json()).then((p) => {
  const c = (p.changes || []).find((x) => x.kind === "new-upload" || x.kind === "new-release");
  if (!c) return;
  const when = (c.at || "").slice(0, 10);
  strip.innerHTML = "";
  const s = document.createElement("span");
  s.textContent = "New transmission \u2014 " + c.title + (when ? " \u00b7 " + when : "");
  strip.append(s);
  strip.hidden = false;
}).catch(() => { /* no pulse yet: the strip stays hidden, nothing is invented */ });
