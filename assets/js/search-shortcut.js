/* "/" focuses the catalogue search from anywhere on the site.
   On the releases index it focuses the filter box; anywhere else it
   goes to the releases index with the box focused. Typing in a field
   is never hijacked, and modified keys are left alone. */
(function () {
  "use strict";
  function focusBox() {
    var box = document.getElementById("f-text");
    if (box) { box.focus(); box.select(); return true; }
    return false;
  }
  if (window.location.hash === "#f-text") focusBox();
  document.addEventListener("keydown", function (e) {
    if (e.key !== "/" || e.metaKey || e.ctrlKey || e.altKey) return;
    var t = e.target;
    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable)) return;
    e.preventDefault();
    if (focusBox()) return;
    var path = window.location.pathname;
    var target = path.indexOf("/releases/") !== -1 ? "index.html#f-text" : "releases/index.html#f-text";
    window.location.href = target;
  });
})();
