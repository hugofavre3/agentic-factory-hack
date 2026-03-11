"""Page 3 — Vue Macro OF (dashboard de pilotage global).

KPI, camembert statuts, tableau de bord manager.
"""

import streamlit as st
import pandas as pd
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data import build_seed_orders

st.set_page_config(page_title="Vue Macro OF", page_icon="📊", layout="wide")

# Init
if "orders" not in st.session_state:
    st.session_state["orders"] = build_seed_orders()
if "agent1_outputs" not in st.session_state:
    st.session_state["agent1_outputs"] = {}
if "agent2_outputs" not in st.session_state:
    st.session_state["agent2_outputs"] = {}
if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = []

orders = st.session_state["orders"]

st.title("📊 Vue Macro OF — Dashboard de pilotage")

# =============================================================================
# KPI
# =============================================================================

st.subheader("Indicateurs clés")

all_statuses = ["Created", "Released", "PartiallyReleased", "Delayed", "ReadyToResume"]
status_counts = {s: 0 for s in all_statuses}
for o in orders.values():
    s = o["status"]
    if s in status_counts:
        status_counts[s] += 1

colors_map = {
    "Created": "🔵",
    "Released": "🟢",
    "PartiallyReleased": "🟡",
    "Delayed": "🔴",
    "ReadyToResume": "✅",
}

cols = st.columns(len(all_statuses))
for i, status in enumerate(all_statuses):
    icon = colors_map.get(status, "")
    cols[i].metric(f"{icon} {status}", status_counts[status])

st.divider()

# =============================================================================
# Graphique statuts
# =============================================================================

st.subheader("Répartition par statut")

chart_data = pd.DataFrame([
    {"Statut": s, "Nombre": c}
    for s, c in status_counts.items() if c > 0
])

if not chart_data.empty:
    st.bar_chart(chart_data, x="Statut", y="Nombre", horizontal=False)
else:
    st.info("Aucun OF traité pour le moment.")

st.divider()

# =============================================================================
# Tableau de bord
# =============================================================================

st.subheader("Tableau de bord OF")

# Filtres
col_f1, col_f2 = st.columns(2)
with col_f1:
    filter_status = st.multiselect(
        "Filtrer par statut :",
        options=all_statuses,
        default=all_statuses,
    )
with col_f2:
    filter_scenario = st.multiselect(
        "Filtrer par scénario :",
        options=["OK", "Moyen", "Critique"],
        default=["OK", "Moyen", "Critique"],
    )

# Construire le tableau
rows = []
for of_id, order in orders.items():
    if order["status"] not in filter_status:
        continue
    if order["scenario"] not in filter_scenario:
        continue

    a1 = st.session_state["agent1_outputs"].get(of_id, {})
    a2 = st.session_state["agent2_outputs"].get(of_id, {})

    rows.append({
        "OF": order["orderNumber"],
        "Scénario": order["scenario"],
        "Produit": order["productCode"],
        "Qté": order["quantity"],
        "Priorité": order["priority"],
        "Échéance": order["dueDate"][:10],
        "Statut": order["status"],
        "Risque": a1.get("risk_level", "—"),
        "Score": a1.get("global_risk_score", "—"),
        "Décision A1": a1.get("decision", "—"),
        "Priorité reprise": a2.get("resume_priority", "—"),
        "ETA (j)": a2.get("overall_eta_days", "—"),
        "Dernier agent": order.get("last_agent", "—"),
    })

if rows:
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("Aucun OF ne correspond aux filtres sélectionnés.")

st.divider()

# =============================================================================
# Watchlist active
# =============================================================================

st.subheader("Watchlist orchestrateur (OF à surveiller)")

watchlist = st.session_state["watchlist"]
if watchlist:
    wl_df = pd.DataFrame(watchlist)
    st.dataframe(wl_df, use_container_width=True, hide_index=True)
else:
    st.info("Watchlist vide — aucun OF en attente de surveillance Agent 2.")

# =============================================================================
# Résumé textuel
# =============================================================================

st.subheader("Résumé")

total = len(orders)
released = sum(1 for o in orders.values() if o["status"] == "Released")
partial = sum(1 for o in orders.values() if o["status"] == "PartiallyReleased")
delayed = sum(1 for o in orders.values() if o["status"] == "Delayed")
ready = sum(1 for o in orders.values() if o["status"] == "ReadyToResume")
created = sum(1 for o in orders.values() if o["status"] == "Created")

if created == total:
    st.markdown("🔵 **Tous les OF sont en attente de traitement.** Lancez Agent 1 depuis le Scenario Playground.")
elif released + ready == total:
    st.markdown("🟢 **Tous les OF sont lancés ou prêts à reprendre.** Production en cours normal.")
else:
    lines = []
    if released:
        lines.append(f"🟢 {released} OF lancé(s) complètement")
    if partial:
        lines.append(f"🟡 {partial} OF en production partielle")
    if delayed:
        lines.append(f"🔴 {delayed} OF différé(s)")
    if ready:
        lines.append(f"✅ {ready} OF prêt(s) à reprendre")
    if created:
        lines.append(f"🔵 {created} OF non traité(s)")
    st.markdown("\n\n".join(lines))
