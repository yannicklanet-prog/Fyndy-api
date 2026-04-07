(function () {
  const WIDGET_ID = "fyndy-widget-fixed";

  function removeOldWidget() {
    const old = document.getElementById(WIDGET_ID);
    if (old) old.remove();
  }

  function getQuery() {
    const url = new URL(window.location.href);
    const q = url.searchParams.get("q");
    if (q && q.trim()) return q.trim();

    const input =
      document.querySelector('input[name="q"]') ||
      document.querySelector('textarea[name="q"]') ||
      document.querySelector('#twotabsearchtextbox') ||
      document.querySelector('input[type="search"]');

    if (input && input.value && input.value.trim()) {
      return input.value.trim();
    }

    return null;
  }

  function detectPageType() {
    const host = window.location.hostname;
    if (host.includes("google")) return "google";
    if (host.includes("brave")) return "brave";
    if (host.includes("amazon")) return "amazon";
    return "other";
  }

  function fallbackOffer(query) {
    return {
      title: `Offres Amazon pour : ${query}`,
      price: null,
      url: `https://www.amazon.fr/s?k=${encodeURIComponent(query)}`,
      site: "Amazon"
    };
  }

  function getAnalysis(score, price, avgPrice) {
    let color = "#f59e0b";
    let emoji = "🟠";
    let label = "Prix correct";
    let verdict = "PEUT MIEUX FAIRE";
    let diffText = "Analyse partielle disponible";

    if (typeof price === "number" && typeof avgPrice === "number" && avgPrice > 0) {
      const diff = ((price - avgPrice) / avgPrice) * 100;

      if (diff <= -10) {
        color = "#16a34a";
        emoji = "🟢";
        label = "BON PLAN";
        verdict = "ACHETER MAINTENANT";
        diffText = `💰 ${Math.round(Math.abs(diff))}% moins cher que le prix moyen`;
      } else if (diff >= 10) {
        color = "#dc2626";
        emoji = "🔴";
        label = "MAUVAIS PRIX";
        verdict = "ATTENDRE";
        diffText = `💸 ${Math.round(diff)}% plus cher que le prix moyen`;
      } else {
        color = "#f59e0b";
        emoji = "🟠";
        label = "Prix correct";
        verdict = "PEUT MIEUX FAIRE";
        diffText = "💰 Prix proche du marché";
      }
    } else {
      if (score >= 80) {
        color = "#16a34a";
        emoji = "🟢";
        label = "BON PLAN";
        verdict = "ACHETER MAINTENANT";
      } else if (score < 60) {
        color = "#dc2626";
        emoji = "🔴";
        label = "MAUVAIS PRIX";
        verdict = "ATTENDRE";
      }
    }

    return { color, emoji, label, verdict, diffText };
  }

  function formatPrice(value) {
    if (value === null || value === undefined || value === "") return "indisponible";
    const n = Number(value);
    if (Number.isNaN(n)) return "indisponible";
    return `${n.toFixed(2).replace(".", ",")} €`;
  }

  function safeScore(query) {
    const q = query.toLowerCase();
    if (q.includes("garmin")) return 75;
    if (q.includes("grohe") || q.includes("hansgrohe")) return 82;
    if (q.includes("iphone")) return 80;
    return 70;
  }

  async function fetchAnalysis(query) {
    try {
      const res = await fetch(`https://fyndy-api.onrender.com/search?q=${encodeURIComponent(query)}`);
      const data = await res.json();

      if (!data || !data.ok) {
        return {
          best_offer: fallbackOffer(query),
          avg_price: null
        };
      }

      return {
        best_offer: data.best_offer || fallbackOffer(query),
        avg_price: data.avg_price ?? null
      };
    } catch (e) {
      console.error("Fyndy search error:", e);
      return {
        best_offer: fallbackOffer(query),
        avg_price: null
      };
    }
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

  function injectWidget(query, offer, avgPrice) {
    removeOldWidget();

    const price = offer && typeof offer.price === "number" ? offer.price : null;
    const score = safeScore(query);
    const analysis = getAnalysis(score, price, avgPrice);

    const widget = document.createElement("div");
    widget.id = WIDGET_ID;
    widget.style.position = "fixed";
    widget.style.top = "110px";
    widget.style.right = "20px";
    widget.style.width = "310px";
    widget.style.background = "white";
    widget.style.border = "1px solid #e5e7eb";
    widget.style.borderRadius = "16px";
    widget.style.boxShadow = "0 10px 30px rgba(0,0,0,0.18)";
    widget.style.padding = "16px";
    widget.style.zIndex = "2147483647";
    widget.style.fontFamily = "Arial, sans-serif";
    widget.style.color = "#111827";

    widget.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <div style="font-size:18px;font-weight:700;">Fyndy</div>
        <div id="fyndy-close-btn" style="cursor:pointer;font-size:22px;line-height:1;">✕</div>
      </div>

      <div style="font-size:16px;font-weight:800;color:${analysis.color};margin-bottom:8px;">
        ${analysis.emoji} ${score}% — ${analysis.label}
      </div>

      <div style="font-size:13px;color:#374151;margin-bottom:10px;">
        Analyse basée sur le marché
      </div>

      <div style="font-size:13px;line-height:1.4;margin-bottom:8px;">
        ${offer.title || `Offres Amazon pour : ${query}`}
      </div>

      <div style="font-size:13px;color:#6b7280;margin-bottom:6px;">
        Source : ${offer.site || "Amazon"}
      </div>

      <div style="font-size:14px;margin-top:8px;">
        Prix détecté : <strong>${formatPrice(price)}</strong>
      </div>

      <div style="font-size:14px;margin-top:8px;">
        Prix moyen estimé : <strong>${formatPrice(avgPrice)}</strong>
      </div>

      <div style="font-size:14px;margin-top:8px;color:${analysis.color};font-weight:700;">
        ${analysis.diffText}
      </div>

      <div style="font-size:15px;font-weight:800;margin-top:14px;margin-bottom:14px;">
        👉 ${analysis.verdict}
      </div>

      <button id="fyndy-open-btn" style="
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

    const closeBtn = document.getElementById("fyndy-close-btn");
    if (closeBtn) {
      closeBtn.addEventListener("click", () => widget.remove());
    }

    const openBtn = document.getElementById("fyndy-open-btn");
    if (openBtn) {
      openBtn.addEventListener("click", () => {
        trackClick({
          query: query,
          product: offer.title || `Offres Amazon pour : ${query}`,
          price: price,
          source: offer.site || "Amazon",
          url: offer.url || `https://www.amazon.fr/s?k=${encodeURIComponent(query)}`
        });

        setTimeout(() => {
          window.open(
            offer.url || `https://www.amazon.fr/s?k=${encodeURIComponent(query)}`,
            "_blank"
          );
        }, 300);
      });
    }
  }

  async function runFyndy() {
    try {
      const pageType = detectPageType();
      if (!["google", "brave", "amazon"].includes(pageType)) return;

      const query = getQuery();
      if (!query) return;

      const result = await fetchAnalysis(query);
      injectWidget(query, result.best_offer, result.avg_price);
    } catch (e) {
      console.error("Fyndy widget global error:", e);
    }
  }

  setTimeout(runFyndy, 1500);
})();
