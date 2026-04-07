(function () {
  const EXISTING_ID = "fyndy-widget";

  function removeExistingWidget() {
    const old = document.getElementById(EXISTING_ID);
    if (old) old.remove();
  }

  function getQueryFromPage() {
    const url = new URL(window.location.href);
    const q = url.searchParams.get("q");
    if (q && q.trim()) return q.trim();

    const input =
      document.querySelector('input[name="q"]') ||
      document.querySelector('textarea[name="q"]') ||
      document.querySelector("#twotabsearchtextbox");

    if (input && input.value && input.value.trim()) {
      return input.value.trim();
    }

    return null;
  }

  function getScore(query) {
    const q = query.toLowerCase();

    if (q.includes("hansgrohe") || q.includes("grohe")) return 85;
    if (q.includes("garmin")) return 75;
    if (q.includes("iphone")) return 82;
    if (q.includes("samsung")) return 78;
    if (q.length > 15) return 70;

    return 55;
  }

  function getVisuals(score) {
    if (score >= 80) {
      return {
        color: "#16a34a",
        label: "BON PLAN",
        verdict: "ACHETER MAINTENANT",
        emoji: "🟢"
      };
    }

    if (score < 60) {
      return {
        color: "#dc2626",
        label: "MAUVAIS PRIX",
        verdict: "ATTENDRE",
        emoji: "🔴"
      };
    }

    return {
      color: "#f59e0b",
      label: "Prix correct",
      verdict: "PEUT MIEUX FAIRE",
      emoji: "🟠"
    };
  }

  async function trackClick(payload) {
    try {
      await fetch("https://fyndy-api.onrender.com/track_click", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });
    } catch (e) {
      console.error("Fyndy tracking error:", e);
    }
  }

  function createWidget(query, offer) {
    removeExistingWidget();

    const score = getScore(query);
    const visuals = getVisuals(score);

    const widget = document.createElement("div");
    widget.id = EXISTING_ID;
    widget.style.position = "fixed";
    widget.style.top = "110px";
    widget.style.right = "20px";
    widget.style.width = "300px";
    widget.style.background = "white";
    widget.style.border = "1px solid #e5e7eb";
    widget.style.borderRadius = "16px";
    widget.style.boxShadow = "0 10px 30px rgba(0,0,0,0.15)";
    widget.style.padding = "16px";
    widget.style.zIndex = "999999";
    widget.style.fontFamily = "Arial, sans-serif";

    const title = offer?.title || `Offres Amazon pour : ${query}`;
    const url = offer?.url || `https://www.amazon.fr/s?k=${encodeURIComponent(query)}`;
    const site = offer?.site || "Amazon";
    const price = offer?.price;

    let priceHtml = `<div style="font-size:14px;margin-top:8px;color:#374151;">Prix indisponible</div>`;
    if (price !== null && price !== undefined && price !== "") {
      priceHtml = `<div style="font-size:14px;margin-top:8px;color:#374151;">Prix détecté : <strong>${price} €</strong></div>`;
    }

    widget.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <div style="font-size:18px;font-weight:700;">Fyndy</div>
        <div id="fyndy-close" style="cursor:pointer;font-size:22px;line-height:1;">✕</div>
      </div>

      <div style="font-size:16px;font-weight:800;color:${visuals.color};margin-bottom:8px;">
        ${visuals.emoji} ${score}% — ${visuals.label}
      </div>

      <div style="font-size:13px;color:#374151;margin-bottom:8px;">
        Analyse basée sur le marché
      </div>

      <div style="font-size:13px;color:#111827;line-height:1.4;margin-bottom:8px;">
        ${title}
      </div>

      <div style="font-size:13px;color:#6b7280;margin-bottom:4px;">
        Source : ${site}
      </div>

      ${priceHtml}

      <div style="font-size:15px;font-weight:800;color:#111827;margin-top:12px;margin-bottom:14px;">
        👉 ${visuals.verdict}
      </div>

      <button id="fyndy-open" style="
        width:100%;
        border:none;
        border-radius:10px;
        padding:12px;
        background:#2563eb;
        color:white;
        font-size:15px;
        font-weight:700;
        cursor:pointer;
      ">
        🔥 Voir la meilleure offre
      </button>
    `;

    document.body.appendChild(widget);

    const closeBtn = document.getElementById("fyndy-close");
    if (closeBtn) {
      closeBtn.addEventListener("click", () => widget.remove());
    }

    const openBtn = document.getElementById("fyndy-open");
    if (openBtn) {
      openBtn.addEventListener("click", async () => {
        await trackClick({
          query: query,
          product: title,
          price: price ?? null,
          source: site,
          url: url
        });

        setTimeout(() => {
          window.open(url, "_blank");
        }, 200);
      });
    }
  }

  async function runFyndy() {
    try {
      const query = getQueryFromPage();
      if (!query) return;

      const res = await fetch(`https://fyndy-api.onrender.com/search?q=${encodeURIComponent(query)}`);
      const data = await res.json();

      if (!data || !data.ok) {
        createWidget(query, null);
        return;
      }

      createWidget(query, data.best_offer || null);
    } catch (e) {
      console.error("Fyndy widget error:", e);
    }
  }

  function start() {
    setTimeout(runFyndy, 1200);
  }

  start();
})();
