/* assets/js/release-week.js — Release Week page wiring (scene/uncle-release-week.html).
 *
 * Progressive enhancement over the pre-rendered page, under the station's
 * Wave-B fallback contract: the HTML ships with the full static content in
 * its pre-release state. On load this script paints the countdown chips
 * from each date's own calendar day, then tries the hand-maintained
 * release file (data/release-week-uncle.json). If that file says the LP is
 * released, the page state flips — state line, release chip, first-capture
 * slot. If the fetch fails for any reason, the pre-rendered page stands.
 *
 * Honesty rule (shared with uncle-watch.js): the archive records a release
 * as released only after a research pass confirms it. This page never
 * flips on the calendar alone — a passed date reads "not yet confirmed".
 * Titles, dates, counts and venues only.
 */
(function () {
  "use strict";

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  /* Resolve against the page's own URL (the search.js pattern), so the
   * fetch works from the scene/ directory this page lives in. */
  function absUrl(path) {
    return new URL(path, document.baseURI).href;
  }

  /* ---- countdown chips (presentation only, computed from the date) ---- */
  function paintWhen(root) {
    var now = new Date();
    var today = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
    Array.prototype.forEach.call(root.querySelectorAll("[data-when]"), function (el) {
      var parts = String(el.getAttribute("data-when") || "").split("-");
      if (parts.length !== 3) return;
      var t = Date.UTC(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
      var days = Math.round((t - today) / 86400000);
      el.textContent =
        days === 0 ? "today" :
        days === 1 ? "tomorrow" :
        days > 1 ? "in " + days + " days" :
        days === -1 ? "yesterday" :
        Math.abs(days) + " days ago";
    });
  }

  /* ---- release state ---- */
  function paintState(data) {
    var stateEl = document.getElementById("rw-state");
    if (!stateEl || !data || !data.release) return;
    var rel = data.release;
    var expected = rel.expected || stateEl.getAttribute("data-expected") || "";

    if (rel.status === "released") {
      stateEl.textContent = "Released — confirmed " + (rel.confirmed_at || "by a research pass") +
        (rel.confirmed_by ? " (" + rel.confirmed_by + ")" : "") + ".";
      stateEl.setAttribute("data-status", "released");
      var chip = document.getElementById("rw-release-chip");
      if (chip) {
        chip.removeAttribute("data-when");
        chip.textContent = "out now";
      }
    } else if (/^\d{4}-\d{2}-\d{2}$/.test(expected)) {
      var now = new Date();
      var today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      var target = new Date(expected + "T00:00:00");
      var days = Math.round((target.getTime() - today.getTime()) / 86400000);
      if (days === 0) {
        stateEl.textContent = "Release day (" + expected + ") — announced, not yet confirmed released by this archive.";
      } else if (days < 0) {
        stateEl.textContent = "Expected " + expected + " has passed — the archive has not yet confirmed the release. The next research pass updates this wire.";
      }
    }

    var cap = data.post_release_flip && data.post_release_flip.signal_watch_capture;
    var slot = document.getElementById("rw-capture");
    if (slot && cap && cap.status === "logged") {
      slot.innerHTML = "First Signal capture after the release: logged " + esc(cap.captured_at || "") +
        (cap.source ? " — " + esc(cap.source) : "") +
        (cap.vault_tracks_watched ? " · " + esc(cap.vault_tracks_watched) + " vault tracks watched" : "") +
        (cap.new_uploads !== null && cap.new_uploads !== undefined ? " · " + esc(cap.new_uploads) + " new uploads in that capture" : "") + ".";
    }
  }

  paintWhen(document);

  if (window.fetch) {
    var dataUrl;
    try { dataUrl = absUrl("../data/release-week-uncle.json"); }
    catch (e) { dataUrl = "../data/release-week-uncle.json"; }
    fetch(dataUrl, { cache: "force-cache" })
      .then(function (r) { if (!r.ok) throw new Error("release-week " + r.status); return r.json(); })
      .then(paintState)
      .catch(function () { /* pre-rendered pre-release state stands */ });
  }
})();
