"""Home — Demo OF partiels bogies — cockpit multi-agents.

Point d'entrée Streamlit multipage.
Lancer avec :
    streamlit run streamlit_app/Home.py
"""

import streamlit as st
from data import build_seed_orders

st.set_page_config(
    page_title="Demo OF partiels bogies — cockpit multi-agents",
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
# Page Home
# =============================================================================

st.title("🏭 Demo OF partiels bogies — cockpit multi-agents")

st.markdown("""
Bienvenue dans le démonstrateur de pilotage d'Ordres de Fabrication partiels (bogies Y32)
avec **deux agents IA** et un **orchestrateur**.

---

### Flux de la solution

```
Agent 1 (Planification OF)
    ↓ output JSON
Orchestrateur (scan + watchlist)
    ↓ watchlist JSON
Agent 2 (Surveillance stock & reprise)
    ↓ décision de reprise
```

### 3 scénarios de démonstration

| Scénario | Stock | Décision attendue | Risque |
|---|---|---|---|
| ✅ **OK** | Tout disponible | `FULL_RELEASE` | LOW |
| ⚠️ **Moyen** | 1 pièce manquante (BRAKE_DISC) | `PARTIAL_RELEASE` | MEDIUM |
| 🛑 **Critique** | 3 pièces critiques absentes | `DELAYED_RELEASE` | HIGH |

### Navigation

Utilisez le **menu latéral** pour naviguer entre les pages :
1. **Scenario Playground** — Testez les 3 scénarios en cliquant sur les boutons agents.
2. **Agent Logs & Details** — Inspectez les inputs/outputs détaillés de chaque agent.
3. **Vue Macro OF** — Dashboard de pilotage global avec KPI et tableau de bord.
""")

st.divider()

# Bouton reset
if st.button("🔄 Réinitialiser la démo", type="secondary"):
    st.session_state["orders"] = build_seed_orders()
    st.session_state["agent1_outputs"] = {}
    st.session_state["agent2_outputs"] = {}
    st.session_state["watchlist"] = []
    st.success("Démo réinitialisée — tous les OF sont revenus en statut Created.")

# Résumé rapide
st.subheader("État courant des OF")
orders = st.session_state["orders"]
cols = st.columns(5)
statuses = ["Created", "Released", "PartiallyReleased", "Delayed", "ReadyToResume"]
colors = {"Created": "🔵", "Released": "🟢", "PartiallyReleased": "🟡", "Delayed": "🔴", "ReadyToResume": "✅"}
for i, status in enumerate(statuses):
    count = sum(1 for o in orders.values() if o["status"] == status)
    cols[i].metric(f"{colors.get(status, '')} {status}", count)
