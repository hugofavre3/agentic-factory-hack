"""Home — Pilotage intelligent des OF partiels — Bogies.

Point d'entrée Streamlit multipage.
Lancer avec :
    streamlit run "Challenge MVP/streamlit_app/Home.py"
"""

import streamlit as st
from data import build_seed_orders

st.set_page_config(
    page_title="Pilotage intelligent des OF partiels — Bogies",
    page_icon="🏭",
    layout="wide",
)

# =============================================================================
# Initialisation session_state
# =============================================================================

def init_state():
    """Seed les données en session si pas encore fait."""
    if "orders" not in st.session_state:
        st.session_state["orders"] = build_seed_orders()
    if "agent1_outputs" not in st.session_state:
        st.session_state["agent1_outputs"] = {}
    if "agent2_outputs" not in st.session_state:
        st.session_state["agent2_outputs"] = {}
    if "watchlist" not in st.session_state:
        st.session_state["watchlist"] = []

init_state()

# =============================================================================
# Sidebar
# =============================================================================

st.sidebar.title("🏭 Pilotage OF Bogies")
st.sidebar.caption(
    "Naviguez entre les vues :\n"
    "1. **Cockpit Jour J** — Supervision terrain\n"
    "2. **Dans la tête de l'IA** — Détail agents\n"
    "3. **Vision Macro & Impact** — Pilotage projet"
)
st.sidebar.divider()
if st.sidebar.button("🔄 Réinitialiser la démo", type="secondary"):
    st.session_state["orders"] = build_seed_orders()
    st.session_state["agent1_outputs"] = {}
    st.session_state["agent2_outputs"] = {}
    st.session_state["watchlist"] = []
    st.session_state.pop("custom_of_status", None)
    st.rerun()

# =============================================================================
# Page Home
# =============================================================================

st.title("🏭 Pilotage intelligent des OF partiels — Bogies")

st.markdown(
    "**Aujourd'hui, quand il manque une pièce, vous lancez quand même, vous stockez à côté, "
    "vous suivez à la main.** On va voir comment deux agents IA vous assistent pour décider vite "
    "et ne plus laisser dormir de valeur en bord de ligne."
)

st.divider()

# --- Fil narratif de la démo ---
st.subheader("🎯 Ce que vous allez voir")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        "### 📋 Cockpit Jour J\n"
        "*Supervision terrain*\n\n"
        "En un coup d'œil : combien d'OF sont bloqués, "
        "lesquels sont prêts à repartir, où sont les risques.\n\n"
        "**→** Simulez 3 scénarios (OK / moyen / critique) "
        "et lancez les agents en un clic."
    )

with col2:
    st.markdown(
        "### 🧠 Dans la tête de l'IA\n"
        "*Détail des agents*\n\n"
        "L'IA n'est pas une boîte noire : vous voyez exactement **pourquoi** "
        "elle recommande un lancement partiel ou un report.\n\n"
        "**→** Stock, historique, SLA, calendrier : tout est explicable."
    )

with col3:
    st.markdown(
        "### 📊 Vision Macro & Impact\n"
        "*Pilotage projet*\n\n"
        "Pour le chef d'atelier ou le responsable supply : "
        "les gains estimés, les OF sous tension, "
        "la répartition des statuts.\n\n"
        "**→** Moins d'OF démarrés pour rien, plus de visibilité."
    )

st.divider()

# --- Flux technique (discret) ---
with st.expander("🔧 Flux technique des agents"):
    st.markdown("""
```
Agent 1 (Décision de lancement)      →  "Complet / Partiel / Décalé"
    ↓ output JSON
Orchestrateur (Watchlist automatique) →  "Quels OF surveiller ?"
    ↓ watchlist JSON
Agent 2 (Surveillance & reprise)     →  "Pièces arrivées ? Reprendre ici."
```

| Scénario démo | Stock | Décision | Risque |
|---|---|---|---|
| ✅ OK | Tout disponible | Lancement complet | Faible |
| ⚠️ Moyen | 1 pièce manquante (freins) | Lancement partiel | Moyen |
| 🛑 Critique | 3 pièces critiques absentes | Report | Élevé |
    """)

st.divider()

# --- État courant ---
st.subheader("📡 État courant des OF")

orders = st.session_state["orders"]
# Exclure custom pour les KPIs de la home
sim_orders = {k: v for k, v in orders.items() if k != "of-custom-001"}

statuses = ["Created", "Released", "PartiallyReleased", "Delayed", "ReadyToResume"]
labels_fr = {
    "Created": "Non traités",
    "Released": "Lancés",
    "PartiallyReleased": "En partiel",
    "Delayed": "Différés",
    "ReadyToResume": "Prêts à reprendre",
}
icons = {"Created": "🔵", "Released": "🟢", "PartiallyReleased": "🟠", "Delayed": "🔴", "ReadyToResume": "✅"}

cols = st.columns(len(statuses))
for i, status in enumerate(statuses):
    count = sum(1 for o in sim_orders.values() if o["status"] == status)
    cols[i].metric(f"{icons[status]} {labels_fr[status]}", count)
