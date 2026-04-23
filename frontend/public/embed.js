// Prediction Lab embed loader. ~1.5 KB minified.
//
// Usage on partner blog:
//   <div data-predlab-match="4321" data-predlab-lang="en"></div>
//   <script async src="https://predictor.nullshift.sh/embed.js"></script>
//
// Every matching div turns into a responsive iframe. Auto-height via
// postMessage back from the embed page.

(function () {
  "use strict";
  var SITE = "https://predictor.nullshift.sh";
  var seen = new WeakSet();

  function mount(el) {
    if (seen.has(el)) return;
    seen.add(el);
    var matchId = el.getAttribute("data-predlab-match");
    if (!matchId) return;
    var lang = el.getAttribute("data-predlab-lang") || "en";

    var iframe = document.createElement("iframe");
    iframe.src = SITE + "/embed/match/" + encodeURIComponent(matchId) + "?lang=" + encodeURIComponent(lang);
    iframe.loading = "lazy";
    iframe.setAttribute("title", "Match prediction — Prediction Lab");
    iframe.setAttribute(
      "sandbox",
      "allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox"
    );
    iframe.style.cssText =
      "width:100%;max-width:480px;min-height:260px;border:0;border-radius:12px;" +
      "box-shadow:0 1px 3px rgba(0,0,0,.08);display:block;";

    el.innerHTML = "";
    el.appendChild(iframe);
  }

  function mountAll() {
    var nodes = document.querySelectorAll("[data-predlab-match]");
    for (var i = 0; i < nodes.length; i++) mount(nodes[i]);
  }

  // Auto-resize from child postMessage. Partner pages receive
  // { type: "predlab-height", height: 320 } when the card is measured.
  window.addEventListener("message", function (e) {
    if (e.origin !== SITE) return;
    var msg = e.data;
    if (!msg || msg.type !== "predlab-height") return;
    var iframes = document.getElementsByTagName("iframe");
    for (var i = 0; i < iframes.length; i++) {
      if (iframes[i].contentWindow === e.source) {
        iframes[i].style.height = Math.max(200, Math.floor(msg.height)) + "px";
        break;
      }
    }
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mountAll);
  } else {
    mountAll();
  }
})();
