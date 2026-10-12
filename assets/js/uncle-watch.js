/* Uncle watch — countdown/status for the announced Fish Narc LP.
 * Reads data-status / data-expected from #uncle-watch-status (rendered by
 * build_circle.py). Text-only, no animation: safe under prefers-reduced-motion.
 * Honesty rule: this archive records "released" only after a research pass
 * confirms it, so pre-release states never claim the LP is out. */
(function () {
  "use strict";
  var el = document.getElementById("uncle-watch-status");
  if (!el) return;
  var status = el.getAttribute("data-status") || "announced";
  var expected = el.getAttribute("data-expected") || "";

  if (status === "released") {
    el.textContent = "Released — confirmed by a research pass. See the scene record for release details.";
    return;
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(expected)) return;

  var now = new Date();
  var today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  var target = new Date(expected + "T00:00:00");
  var days = Math.round((target.getTime() - today.getTime()) / 86400000);

  if (days > 1) {
    el.textContent = "Announced — expected " + expected + " (" + days + " days to go).";
  } else if (days === 1) {
    el.textContent = "Announced — expected " + expected + " (tomorrow).";
  } else if (days === 0) {
    el.textContent = "Release day (" + expected + ") — not yet confirmed released by this archive.";
  } else {
    el.textContent = "Expected " + expected + " has passed — the archive has not yet confirmed the release. The next research pass will update this watch.";
  }
})();
