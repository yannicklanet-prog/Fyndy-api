(function () {
  let fyndyButton = null;
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

    const raw = String(price).replace("€", "").replace(",", ".").trim();
    const n = Number(raw);

    if (Number.isNaN(n)) {
      return "Voir le prix";
    }

    return `${n.toFixed(2).replace(".", ",")} €`;
  }

  function isValidUrl(url) {
    return typeof url === "string" && /^https?:\/\//i.test(url);
  }

  function removePopup() {
    if (fyndyBox) {
      fyndyBox.remove();
      fyndyBox = null;
    }
  }

  function showSmallMessage(container, message, color = "#6b7280") {
    const old = container.querySelector(".fyndy-inline-message");
    if (old) old.remove();

    const div = document.createElement("div");
    div.className = "fyndy-inline-message";
    div.textContent = message;
    div.style.marginTop = "10px";
    div.style.fontSize = "12px";
    div.style.color = color;

    container.appendChild(div);
  }

  async function trackClick(payload) {
    try {
      const response = await fetch("https://fyndy-api.onrender.com/track_click", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        console.error("Fyndy track_click HTTP error:", response.status);
        return false;
      }

      const data = await response.json().catch(() => null);
      console.log("Fyndy tracking OK:", data);
      return true;
    } catch (error) {
      console.error("Fyndy tracking ERROR:", error);
      return false;
    }
  }

  async function openOffer(url, container, payload) {
    if (!isValidUrl(url)) {
      showSmallMessage(container, "Lien indisponible.", "#b42318");
      return;
    }

    const tracked = await trackClick(payload);

    if (!tracked) {
      showSmallMessage(container, "Tracking impossible, ouverture quand même.", "#b45309");
    }

    try {
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (error) {
      console.error("Fyndy open error:", error);
      showSmallMessage(container, "Impossible d’ouvrir le lien.", "#b42318");
    }
  }

  function createPopup(data, currentQuery) {
    removePopup();

    const offer = data.best_offer || data.lowest_offer;
    if (!offer) return;

    const score = offer.review_score;
    const hasRealPrice =
      offer.price !== null &&
      offer.price !== undefined &&
      offer.price !== "";

    const priceDisplay = formatPrice(offer.price);
    const buttonLabel = hasRealPrice ? "Voir l’offre" : "Voir le prix";

    const urgencyText = "⚡ Bon prix actuellement (peut varier)";
    const comparisonText = "💸 Prix inférieur aux autres vendeurs";

    const proofText =
      score !== null && score !== undefined
        ? `✔ ${score}% d’acheteurs satisfaits`
        : "✔ Données partielles disponibles";

    const reassuranceText =
      score !== null && score !== undefined
        ? "✔ Produit validé par de vrais acheteurs"
        : "✔ Vérification en cours";

    const scoreHTML =
      score !== null && score !== undefined
        ? `
          <div style="margin-top:10px;font-weight:700;color:${getScoreColor(score)};font-size:13px;">
            Score avis : ${score}%
          </div>
        `
        : `
          <div style="margin-top:10px;color:#6b7280;font-size:13px;">
            Avis : indisponible
          </div>
        `;

    const box = document.createElement("div");
    box.id = "fyndy-box";
    box.style.position = "fixed";
    box.style.bottom = "70px";
    box.style.right = "20px";
    box.style.width = "290px";
    box.style.background = "white";
    box.style.borderRadius = "12px";
    box.style.boxShadow = "0 10px 30px rgba(0,0,0,0.25)";
    box.style.border = "1px solid #e5e7eb";
    box.style.zIndex = "999999";
    box.style.fontFamily = "Arial, sans-serif";

    box.innerHTML = `
      <div id="fyndy-inner" style="padding:16px;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <strong style="font-size:18px;">Fyndy</strong>
          <span id="fyndy-close" style="cursor:pointer;font-size:20px;line-height:1;">✕</span>
        </div>

        <div style="margin-top:12px;font-weight:700;font-size:15px;color:#111827;">
          💡 Offre fiable détectée
        </div>

        <div style="margin-top:8px;font-size:12px;color:#dc2626;font-weight:700;">
          ${urgencyText}
        </div>

        <div style="margin-top:6px;font-size:12px;color:#16a34a;font-weight:700;">
          ${comparisonText}
        </div>

        <div style="margin-top:12px;font-size:14px;color:#111827;line-height:1.45;">
          ${offer.title || "Produit"}
        </div>

        <div style="margin-top:10px;font-size:22px;font-weight:800;color:#111827;">
          ${priceDisplay}
        </div>

        <div style="margin-top:6px;color:#6b7280;font-size:13px;">
          ${offer.site || "Source inconnue"}
        </div>

        ${scoreHTML}

        <div style="margin-top:8px;font-size:13px;font-weight:700;color:#16a34a;">
          ${proofText}
        </div>

        <div style="margin-top:6px;font-size:12px;color:#374151;">
          ${reassuranceText}
        </div>

        <button id="fyndy-open-offer" style="
          margin-top:14px;
          width:100%;
          background:#2563eb;
          color:white;
          border:none;
          padding:12px;
          border-radius:8px;
          cursor:pointer;
          font-weight:800;
          font-size:14px;
        ">
          ${buttonLabel}
        </button>
      </div>
    `;

    document.body.appendChild(box);
    fyndyBox = box;

    const closeBtn = document.getElementById("fyndy-close");
    if (closeBtn) {
      closeBtn.onclick = removePopup;
    }

    const openBtn = document.getElementById("fyndy-open-offer");
    const inner = document.getElementById("fyndy-inner");

    if (openBtn && inner) {
      openBtn.onclick = async function (event) {
        event.preventDefault();
        event.stopPropagation();

        await openOffer(offer.url, inner, {
          query: currentQuery,
          product: offer.title || currentQuery,
          price: offer.price ?? null,
          source: offer.site || "inconnu",
          url: offer.url || null
        });
      };
    }
  }

  async function runFyndy() {
    const queryInput =
      document.querySelector("input[name='q']") ||
      document.querySelector("textarea[name='q']") ||
      document.querySelector("#searchbox input") ||
      document.querySelector("#twotabsearchtextbox");

    if (!queryInput) {
      console.log("Fyndy: aucun champ de recherche trouvé");
      return;
    }

    const text = (queryInput.value || "").trim();
    if (!text) {
      console.log("Fyndy: recherche vide");
      return;
    }

    try {
      const response = await fetch(
        `https://fyndy-api.onrender.com/search?q=${encodeURIComponent(text)}`
      );

      if (!response.ok) {
        console.error("Fyndy search HTTP error:", response.status);
        return;
      }

      const data = await response.json();
      console.log("Fyndy search OK:", data);
      createPopup(data, text);
    } catch (error) {
      console.error("Fyndy search ERROR:", error);
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
    btn.style.background = "#2563eb";
    btn.style.color = "white";
    btn.style.border = "none";
    btn.style.borderRadius = "8px";
    btn.style.cursor = "pointer";
    btn.style.fontWeight = "700";
    btn.style.boxShadow = "0 8px 20px rgba(37,99,235,0.4)";

    btn.onclick = runFyndy;

    document.body.appendChild(btn);
    fyndyButton = btn;
  }

  setTimeout(addButton, 1500);
})();
