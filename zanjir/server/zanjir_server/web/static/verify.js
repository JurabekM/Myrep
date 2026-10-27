// PDF faylni brauzerda SHA-256 bilan tekshirish (fayl serverga yuborilmaydi).
(function () {
  var input = document.getElementById("file");
  var out = document.getElementById("result");
  if (!input || !out || !window.crypto || !window.crypto.subtle) return;
  input.addEventListener("change", function () {
    var file = input.files && input.files[0];
    if (!file) return;
    file.arrayBuffer().then(function (buf) {
      return window.crypto.subtle.digest("SHA-256", buf);
    }).then(function (digest) {
      var hex = Array.prototype.map.call(new Uint8Array(digest), function (b) {
        return b.toString(16).padStart(2, "0");
      }).join("");
      var ok = hex === input.dataset.expected;
      out.textContent = ok ? input.dataset.match : input.dataset.mismatch;
      out.className = ok ? "ok" : "bad";
    });
  });
})();
