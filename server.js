const express = require("express");
const cors = require("cors");

const app = express();

// Autorise les appels depuis l'extension / navigateur
app.use(cors());
app.use(express.json());

// Port Render (obligatoire) ou port local
const PORT = process.env.PORT || 3333;

// Clé API (optionnelle mais recommandée)
const API_KEY = process.env.FYNDY_API_KEY || "";

// Petite fonction : vérifier la clé si elle existe
function checkKey(req) {
  // Si aucune clé n'est définie sur Render, on ne bloque pas (mode démo simple)
  if (!API_KEY) return true;

  // On accepte soit:
  // - header: x-api-key
  // - ou paramètre URL: ?key=...
  const headerKey = req.headers["x-api-key"];
  const urlKey = req.query.key;

  return headerKey === API_KEY || urlKey === API_KEY;
}

// Route santé (pour tester que le service est en ligne)
app.get("/health", (req, res) => {
  res.json({ ok: true, service: "fyndy-api", port: PORT });
});

// Route décision (démo)
app.get("/api/decision", (req, res) => {
  if (!checkKey(req)) {
    return res.status(401).json({ ok: false, error: "Clé API invalide" });
  }

  const q = (req.query.q || "").toString();

  // --- Simulation "IA" ---
  const isPrecise = /[a-zA-Z]+\s*[0-9]{2,}/.test(q); // ex: "Grohe S240"
  const decision_status = isPrecise ? "Strong" : "Medium";
  const confidence_score = isPrecise ? 86 : 82;

  const type = isPrecise ? "best_price" : "best_value";
  const label = isPrecise ? "Best Price Verified" : "Meilleur rapport qualité/prix";

  const price_positioning = isPrecise ? "Best price detected" : "Top value detected";
  const manipulation_risk = "Low";
  const trusted_environment = "Trusted";

  // Exemple de réponse produit
  const decision = {
    type,
    label,
    price: isPrecise ? 258 : 273,
    currency: "€",
    merchant: isPrecise ? "Cedeo" : "Leroy Merlin",
    shipping: isPrecise ? "Livraison 24-48h" : "Livraison 2-3 jours",
    url: "https://example.com/product"
  };

  // IMPORTANT : champs au niveau racine (pour éviter les — / undefined)
  res.json({
    ok: true,
    query: q,
    decision_status,
    confidence_score,
    price_positioning,
    manipulation_risk,
    trusted_environment,
    decision
  });
});

// Lancement serveur
app.listen(PORT, () => {
  console.log(`Fyndy API running on port ${PORT}`);
});
