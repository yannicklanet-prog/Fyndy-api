import express from "express";

const app = express();

// Render fournit PORT automatiquement
const PORT = process.env.PORT || 3333;

// --- CORS ultra permissif pour démo extension (sinon ça bloque) ---
app.use((req, res, next) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");
  if (req.method === "OPTIONS") return res.sendStatus(204);
  next();
});

// --- Helpers ---
function clamp(n, a, b) {
  const x = Number(n);
  if (!Number.isFinite(x)) return a;
  return Math.max(a, Math.min(b, x));
}

function isPreciseQuery(q) {
  if (!q) return false;
  const tokens = q.trim().split(/\s+/).filter(Boolean);
  if (tokens.length < 2) return false;

  const hasAlphaNumModel = /[A-Za-z]{1,}\d{2,}|\d{2,}[A-Za-z]{1,}/.test(q);
  const has3Tokens = tokens.length >= 3;

  return hasAlphaNumModel || has3Tokens;
}

function computeTrustSignals(query) {
  // Signaux stables (pas de “prix qui bouge toutes les 3 secondes”)
  const q = (query || "").trim();
  const precise = isPreciseQuery(q);

  // Fiabilité (0-100)
  let reliability = 78 + (precise ? 10 : 4) + Math.min(8, Math.floor(q.length / 10));
  reliability = clamp(reliability, 60, 95);

  // Avis positifs (%)
  let positiveReviews = 90 + (precise ? 5 : 2);
  positiveReviews = clamp(positiveReviews, 88, 98);

  // Risque manipulation
  let risk = "Faible";
  if (!precise) risk = "Modéré";
  if (q.length < 6) risk = "Élevé";

  // Couleur (pour UI)
  const reviewColor = positiveReviews >= 95 ? "green" : positiveReviews >= 92 ? "orange" : "red";
  const riskColor = risk === "Faible" ? "green" : risk === "Modéré" ? "orange" : "red";

  return {
    reliability_score: reliability,
    positive_reviews_pct: positiveReviews,
    manipulation_risk: risk,
    review_signal: positiveReviews >= 95 ? "Fort" : positiveReviews >= 92 ? "Moyen" : "Faible",
    colors: {
      reviews: reviewColor,
      risk: riskColor
    }
  };
}

/**
 * Démo “vendable” : on ne fait PAS comparateur.
 * On renvoie 1 recommandation :
 * - soit “Meilleur prix” si requête précise
 * - soit “Meilleur rapport qualité/prix” sinon
 *
 * On peut ensuite brancher une vraie source (sans changer l’extension).
 */
function buildDecision(query) {
  const q = (query || "").trim();
  const precise = isPreciseQuery(q);

  // Demo: prix stable calculé depuis le texte (donc identique pour tous les testeurs)
  let seed = 0;
  for (let i = 0; i < q.length; i++) seed += q.charCodeAt(i) * (i + 1);

  // Prix "cohérent" (ex: 49€ à 499€) — stable
  const base = 49 + (seed % 451);
  const shipping = precise ? "Livraison 24–72h" : "Livraison standard";

  // Site "neutre" : pour la démo, on met un placeholder crédible.
  // Quand on branchera de vrais liens, ce sera remplacé.
  const merchant = precise ? "Marchand certifié" : "Sélection Fyndy";
  const url = "https://www.google.com/search?q=" + encodeURIComponent(q);

  const label = precise ? "Meilleur prix trouvé" : "Meilleur rapport qualité/prix";
  const decision_status = precise ? "Décision d’achat immédiate" : "Décision optimisée (équilibre prix / confiance)";

  return {
    label,
    price: base,
    currency: "€",
    merchant,
    shipping,
    url,
    decision_status
  };
}

// --- Routes ---
app.get("/health", (req, res) => {
  res.json({ ok: true, service: "fyndy-api", status: "healthy" });
});

app.get("/api/decision", (req, res) => {
  const q = String(req.query.q || "").trim();
  if (!q) {
    return res.status(400).json({ ok: false, error: "Missing query parameter: q" });
  }

  const decision = buildDecision(q);
  const trust = computeTrustSignals(q);

  return res.json({
    ok: true,
    query: q,
    decision: {
      label: decision.label,
      price: decision.price,
      currency: decision.currency,
      merchant: decision.merchant,
      shipping: decision.shipping,
      url: decision.url
    },
    metrics: {
      decision_status: decision.decision_status,
      reliability_score: trust.reliability_score,
      positive_reviews_pct: trust.positive_reviews_pct,
      review_signal: trust.review_signal,
      manipulation_risk: trust.manipulation_risk,
      colors: trust.colors
    }
  });
});

// --- Start ---
app.listen(PORT, () => {
  console.log(`Fyndy API running on port ${PORT}`);
});
