/* Covers: the typographic sleeve is always underneath. A picture only
   shows once it has really loaded; a failed or tiny one is removed. */
(function () {
  var MIN = 100;
  function ok(img) {
    var box = img.closest(".cover"); if (!box) return;
    if (img.naturalWidth >= MIN) box.setAttribute("data-state", "ok");
    else dead(img);
  }
  function dead(img) {
    var box = img.closest(".cover"); if (box) box.setAttribute("data-state", "dead");
    img.removeAttribute("srcset"); img.remove();
  }
  function hook(img) {
    if (img.complete) { (img.naturalWidth ? ok : dead)(img); return; }
    img.addEventListener("load", function () { ok(img); }, { once: true });
    img.addEventListener("error", function () { dead(img); }, { once: true });
  }
  function run() { document.querySelectorAll(".cover img").forEach(hook); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", run); else run();
})();
