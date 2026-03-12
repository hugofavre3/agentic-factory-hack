"""Home — Pilotage des retards de production bogies par IA — Maestro & Sentinelle.

Point d'entrée Streamlit multipage.
Lancer avec :
    streamlit run "Challenge MVP/streamlit_app/Home.py"
"""

import streamlit as st
from data import build_seed_orders

st.set_page_config(
    page_title="Pilotage des retards — Maestro & Sentinelle",
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
    if "maestro_outputs" not in st.session_state:
        st.session_state["maestro_outputs"] = {}
    if "sentinelle_outputs" not in st.session_state:
        st.session_state["sentinelle_outputs"] = {}
    if "watchlist" not in st.session_state:
        st.session_state["watchlist"] = []

init_state()

# =============================================================================
# Sidebar
# =============================================================================

st.sidebar.title("🏭 Maestro & Sentinelle")
st.sidebar.caption(
    "Naviguez entre les vues :\n"
    "1. **Cockpit d'anticipation** — Risques et inputs\n"
    "2. **Maestro & Sentinelle** — Décisions et impacts\n"
    "3. **Vision Macro** — Impact global des décisions IA"
)
st.sidebar.divider()
if st.sidebar.button("🔄 Réinitialiser la démo", type="secondary"):
    st.session_state["orders"] = build_seed_orders()
    st.session_state["maestro_outputs"] = {}
    st.session_state["sentinelle_outputs"] = {}
    st.session_state["watchlist"] = []
    st.rerun()

# =============================================================================
# Page Home
# =============================================================================

st.title("🏭 Pilotage des retards de production bogies par IA")
st.markdown("## Maestro & Sentinelle")

st.markdown(
    "**Dans une industrie où l'on ne peut pas s'arrêter en plein milieu d'un bogie, "
    "l'IA anticipe les risques de blocage bien avant qu'ils n'arrivent.**\n\n"
    "La question clé : *\"Si je lance maintenant, ai-je un risque réaliste de me retrouver "
    "coincé faute de pièces à l'étape X, ou bien les pièces auront-elles très probablement "
    "eu le temps d'arriver avant que la ligne ne l'atteigne ?\"*"
)

st.divider()

# --- Les deux agents ---
st.subheader("🎯 Deux agents, un objectif : anticiper, pas subir")

col1, col2 = st.columns(2)

with col1:
    st.markdown(
        "### 🎼 Maestro\n"
        "*L'assistant planificateur*\n\n"
        "Regarde en avance le film de production : étapes, "
        "temps de passage, stock, délais fournisseurs, historique.\n\n"
        "**Produit** :\n"
        "- Un niveau de risque d'arrêt (🟢 / 🟠 / 🔴)\n"
        "- Une recommandation de lancement ou replanification\n"
        "- Un plan de commande fournisseur\n"
        "- Un mail fournisseur simulé"
    )

with col2:
    st.markdown(
        "### 🔭 Sentinelle\n"
        "*L'agent qui surveille*\n\n"
        "Surveille les hypothèses prises par Maestro et "
        "actualise en continu le risque de retard.\n\n"
        "**Produit** :\n"
        "- Mise à jour du risque (levé / confirmé)\n"
        "- Suivi des livraisons fournisseurs\n"
        "- Impact actualisé sur la date de fin\n"
        "- Proposition de reprogrammation si nécessaire"
    )

st.divider()

# --- Les 3 scénarios ---
st.subheader("📋 Trois scénarios de démo")

col_ok, col_moy, col_crit = st.columns(3)

with col_ok:
    st.markdown(
        "### ✅ OK\n"
        "Les pièces sont là ou arriveront bien avant l'étape "
        "qui les utilise. Maestro valide : *\"On lance comme prévu.\"*"
    )

with col_moy:
    st.markdown(
        "### ⚠️ Moyen\n"
        "Une pièce manque, ETA serrée. Maestro recommande un "
        "créneau décalé et surveille le risque. "
        "Sentinelle confirme ou lève l'alerte."
    )

with col_crit:
    st.markdown(
        "### 🛑 Critique\n"
        "Blocage quasi certain. Maestro propose de ne pas "
        "lancer et donne des créneaux de reprogrammation. "
        "Sentinelle actualise si la situation s'améliore."
    )

st.divider()

st.caption(
    "💡 *On ne parle plus de gérer les casses une fois qu'on est bloqué, "
    "mais de voir 2–3 jours à l'avance où ça pourrait coincer, "
    "et d'ajuster le planning en conséquence.*"
)
