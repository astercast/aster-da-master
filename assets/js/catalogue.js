/* The home catalogue: find a release by title. Plain enhancement: without
   this file every year still opens and every release is a link. */
(function () {
  "use strict";
  var box = document.getElementById("find");
  var out = document.getElementById("cat-count");
  if (!box || !out) return;
  var years = [].slice.call(document.querySelectorAll(".year"));
  var rows = [].slice.call(document.querySelectorAll(".year li"));
  var base = out.textContent;
  var was = years.map(function (d) { return d.open; });
  box.addEventListener("input", function () {
    var v = box.value.trim().toLowerCase(), n = 0;
    rows.forEach(function (li) {
      var hit = !v || li.getAttribute("data-t").indexOf(v) > -1;
      li.hidden = !hit; if (hit) n++;
    });
    years.forEach(function (d, i) {
      var any = !!d.querySelector("li:not([hidden])");
      d.hidden = !any;
      d.open = v ? any : was[i];
    });
    out.textContent = v ? (n === 0 ? "No match" : n === 1 ? "1 release" : n + " releases") : base;
  });
})();
