(function () {
  let fyndyBox = null;

  function getScoreColor(score) {
    if (score >= 80) return "#16a34a";
    if (score >= 60) return "#f59e0b";
    return "#dc2626";
  }

  function formatPrice(price) {
    if (price === null || price === undefined || price === "") {
      return "Voir le prix";
    }

    const n = Number(String(price).replace(",", ".").replace("€", "").trim());
    if (Number.isNaN(n)) {
      return "Voir le prix";
    }

    return `${n.toFixed(2).replace(".", ",")} €`;
  }

  function createPopup(data) {
    if (fyndyBox) {
      fyndyBox.remove();
    }

    const offer = data.best_offer || data.lowest_offer;
    if (!offer) return;

    const box = document.createElement("div");
    box.id = "fyndy-box";

    const score = offer.review_score;
    const hasRealPrice =
      offer.price !== null &&
      offer.price !== undefined &&
      offer.price !== "";

    let scoreHTML = "";

    if (score === null || score === undefined) {
      scoreHTML = `
        <div style="margin-top:10px;color:#6b7280;font-size:13px;">
          Avis : indisponible
        </div>
      `;
    } else {
      const color = getScoreColor(score);
      scoreHTML = `
        <div style="margin-top:10px;font-weight:600;color:${color};font-size:13px;">
          Score avis : ${score}%
        </div>
      `;
    }

    const priceDisplay = formatPrice(offer.price);
    const buttonLabel = hasRealPrice ? "Voir l’offre" : "💡 Voir le prix réel";

    box.innerHTML = `
      <div style="font-family:Arial, sans-serif;padding:16px;width:280px;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <strong style="font-size:18px;">Fyndy</strong>
          <span id="fyndy-close" style="cursor:pointer;font-size:20px;line-height:1;">✕</span>
        </div>

        <div style="margin-top:12px;font-weight:700;font-size:15px;">
          🔥 Meilleur vendeur fiable
        </div>

        <div style="margin-top:12px;font-size:14px;line-height:1.45;color:#111827;">
          ${offer.title || "Produit"}
        </div>

        <div style="margin-top:10px;font-size:20px;font-weight:700;color:#111827;">
          ${priceDisplay}
        </div>

        <div style="margin-top:6px;color:#6b7280;font-size:13px;">
          ${offer.site || "Source inconnue"}
        </div>

        ${scoreHTML}

        <a href="${offer.url || "#"}" target="_blank" rel="noopener noreferrer" style="text-decoration:none;">
          <button style="
            margin-top:14px;
            width:100%;
            background:#3b82f6;
            color:white;
            border:none;
            padding:11px 12px;
            border-radius:8px;
            cursor:pointer;
            font-weight:600;
            font-size:14px;
          ">
            ${buttonLabel}
          </button>
        </a>
      </div>
    `;

    box.style.position = "fixed";
    box.style.bottom = "20px";
    box.style.right = "20px";
    box.style.background = "white";
    box.style.borderRadius = "12px";
    box.style.boxShadow = "0 10px 30px rgba(0,0,0,0.20)";
    box.style.zIndex = "999999";
    box.style.border = "1px solid #e5e7eb";

    document.body.appendChild(box);
    fyndyBox = box;

    const closeBtn = document.getElementById("fyndy-close");
    if (closeBtn) {
      closeBtn.onclick = () => box.remove();
    }
  }

  async function runFyndy() {
    const queryInput =
      document.querySelector("input[name='q']") ||
      document.querySelector("textarea[name='q']") ||
      document.querySelector("#twotabsearchtextbox");

    if (!queryInput) return;

    const text = (queryInput.value || "").trim();
    if (!text) return;

    try {
      const res = await fetch(
        `https://fyndy-api.onrender.com/search?q=${encodeURIComponent(text)}`
      );
      const data = await res.json();
      createPopup(data);
    } catch (e) {
      console.log("Fyndy error", e);
    }
  }

  function addButton() {
    if (document.getElementById("fyndy-btn")) return;

    const btn = document.createElement("button");
    btn.id = "fyndy-btn";
    btn.innerText = "Fyndy";

    btn.style.position = "fixed";
    btn.style.bottom = "20px";
    btn.style.right = "20px";
    btn.style.zIndex = "999999";
    btn.style.padding = "10px 15px";
    btn.style.background = "#3b82f6";
    btn.style.color = "white";
    btn.style.border = "none";
    btn.style.borderRadius = "8px";
    btn.style.cursor = "pointer";
    btn.style.fontWeight = "600";
    btn.style.boxShadow = "0 8px 20px rgba(59,130,246,0.35)";

    btn.onclick = runFyndy;

    document.body.appendChild(btn);
  }

  setTimeout(addButton, 2000);
})();
