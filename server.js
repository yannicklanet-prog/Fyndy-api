const express = require("express");
const cors = require("cors");

const app = express();

// CORS (simple pour démo)
app.use(cors());
app.use(express.json());

// Health check
app.get("/health", (req, res) => {
  res.json({ ok: true, service: "fyndy-api", port: process.env.PORT || 3333 });
});

// Decision endpoint (démo)
app.get("/api/decision", (req, res) => {
  const q = (req.query.q || "test").toString();

  // Démo: on alterne "meilleur prix" / "meilleur rapport qualité/prix"
  const isPrecise = /\b([A-Za-z]{2,}\s*\d{2,})\b/.test(q) || q.length <= 10;

  if (isPrecise) {
    return res.json({
      ok: true,
      query: q,
      decision_status: "Strong",
      confidence_score: 86,
      price_positioning: "Best price detected",
      manipulation_risk: "Low",
      trusted_environment: "Trusted",
      decision: {
        type: "best_price",
        label: "Best Price Verified",
        price: 258,
        currency: "€",
        merchant: "Cedeo",
        shipping: "Livraison 24-48h",
      },
    });
  }

  return res.json({
    ok: true,
    query: q,
    decision_status: "Medium",
    confidence_score: 82,
    price_positioning: "Top value detected",
    manipulation_risk: "Low",
    trusted_environment: "Trusted",
    decision: {
      type: "best_value",
      label: "Meilleur rapport qualité/prix",
      price: 273,
      currency: "€",
      merchant: "Leroy Merlin",
      shipping: "Livraison 2-3 jours",
    },
  });
});

// IMPORTANT Render : écouter process.env.PORT
const PORT = process.env.PORT || 3333;
app.listen(PORT, "0.0.0.0", () => {
  console.log(`Fyndy API running on port ${PORT}`);
});
