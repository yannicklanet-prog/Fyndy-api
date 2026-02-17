import express from "express";
import cors from "cors";

const app = express();

// (optionnel) JSON si tu ajoutes des POST plus tard
app.use(express.json());

// CORS large (pas dangereux si la clé est obligatoire)
app.use(
  cors({
    origin: true,
    methods: ["GET", "POST", "OPTIONS"],
    allowedHeaders: ["Content-Type", "X-Fyndy-Key"],
  })
);

// ----- Sécurité : clé obligatoire -----
// La clé doit être envoyée dans l'en-tête: X-Fyndy-Key
function requireApiKey(req, res, next) {
  const serverKey = process.env.FYNDY_API_KEY;
  if (!serverKey) {
    return res.status(500).json({ ok: false, error: "Server key not set" });
  }

  const clientKey = req.header("X-Fyndy-Key");
  if (!clientKey || clientKey !== serverKey) {
    return res.status(401).json({ ok: false, error: "Unauthorized" });
  }

  next();
}

// ----- Health (sans clé si tu veux, ou avec clé si tu préfères) -----
// Ici je le laisse PUBLIC pour diagnostiquer facilement
app.get("/health", (req, res) => {
  res.json({ ok: true, service: "fyndy-api", port: process.env.PORT || 10000 });
});

// ----- Endpoint décision (protégé par clé) -----
app.get("/api/decision", requireApiKey, (req, res) => {
  const q = (req.query.q || "").toString().trim();

  // Démo: réponse simulée (à remplacer par ta vraie logique plus tard)
  const isPrecise = q.length >= 6 && /\d/.test(q);

  const payload = {
    ok: true,
    query: q,
    decision_status: isPrecise ? "Strong" : "Medium",
    confidence_score: isPrecise ? 86 : 82,
    price_positioning: isPrecise ? "Best price detected" : "Top value detected",
    manipulation_risk: "Low",
    trusted_environment: "Trusted",
    decision: isPrecise
      ? {
          type: "best_price",
          label: "Best Price Verified",
          price: 258,
          currency: "€",
          merchant: "Cedeo",
          shipping: "Livraison 24-48h",
          url: "https://example.com/product",
        }
      : {
          type: "best_value",
          label: "Meilleur rapport qualité/prix",
          price: 273,
          currency: "€",
          merchant: "Leroy Merlin",
          shipping: "Livraison 2-3 jours",
          url: "https://example.com/product",
        },
  };

  res.json(payload);
});

// Render impose le PORT
const PORT = process.env.PORT || 10000;
app.listen(PORT, () => {
  console.log(`Fyndy API running on port ${PORT}`);
});
