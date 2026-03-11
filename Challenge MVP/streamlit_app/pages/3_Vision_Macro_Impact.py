"""Page 3 — Vision Macro & Impact (Pilotage Projet).

Impact du produit : moins de blocages, plus de fluidité.
"""

import streamlit as st
import pandas as pd
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data import build_seed_orders

st.set_page_config(page_title="Vision Macro & Impact", page_icon="📊", layout="wide")

# --- Init ---
if "orders" not in st.session_state:
    st.session_state["orders"] = build_seed_orders()
if "agent1_outputs" not in st.session_state:
    st.session_state["agent1_outputs"] = {}
if "agent2_outputs" not in st.session_state:
    st.session_state["agent2_outputs"] = {}
if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = []

orders = st.session_state["orders"]
sim_orders = {k: v for k, v in orders.items() if k != "of-custom-001"}

# =============================================================================
# Titre + accroche
# =============================================================================

st.title("📊 Impact du produit : Moins de blocages, plus de fluidité")

st.markdown(
    "*Cette vue s'adresse aux responsables de production et supply chain. "
    "Elle montre la valeur du pilotage par agents : moins d'OF commencés \"pour rien\", "
    "une meilleure anticipation des retards, et une réduction du temps de sommeil des encours.*"
)

st.divider()

# =============================================================================
# Indicateurs de performance — Gains estimés
# =============================================================================

st.subheader("🏆 Gains estimés sur la période")

# Calculer des métriques dynamiques basées sur les outputs
a1_outputs = st.session_state["agent1_outputs"]
a2_outputs = st.session_state["agent2_outputs"]

total_of = len(sim_orders)
of_analysed = sum(1 for k in sim_orders if k in a1_outputs)
of_partial = sum(1 for k, o in sim_orders.items() if o["status"] == "PartiallyReleased")
of_delayed = sum(1 for k, o in sim_orders.items() if o["status"] == "Delayed")
of_resumed = sum(1 for k, o in sim_orders.items() if o["status"] == "ReadyToResume")
of_released = sum(1 for k, o in sim_orders.items() if o["status"] == "Released")

# Alertes critiques évitées = OF delayed au lieu d'être lancés sans vérification
alerts_avoided = of_delayed

# Taux de reprise auto = OF passés en ReadyToResume / OF partiels ou delayed traités par Agent 2
a2_treated = len([k for k in sim_orders if k in a2_outputs])
auto_resume_rate = int(of_resumed / a2_treated * 100) if a2_treated > 0 else 0

m1, m2, m3, m4 = st.columns(4)

m1.metric(
    "🕐 Temps d'attente moyen par OF",
    "−30%",
    help="Estimé : grâce à la reprise ciblée au bon moment, les OF ne dorment plus en bord de ligne.",
)
m2.metric(
    "🛡️ Alertes critiques évitées",
    f"{alerts_avoided} OF décalé(s)",
    help="OF pour lesquels l'IA a recommandé un report plutôt qu'un lancement qui aurait bloqué la ligne.",
)
m3.metric(
    "🤖 Taux de reprise assistée",
    f"{auto_resume_rate}%" if a2_treated > 0 else "—",
    help="Pourcentage d'OF partiels pour lesquels Agent 2 a détecté la disponibilité des pièces automatiquement.",
)
m4.metric(
    "📋 OF analysés par les agents",
    f"{of_analysed}/{total_of}",
    help="Nombre d'OF traités par Agent 1 sur le total disponible.",
)

# =============================================================================
# Encadré "Résumé valeur"
# =============================================================================

st.divider()

val1, val2, val3 = st.columns(3)
val1.markdown(
    "### 🏭 Moins d'OF démarrés pour rien\n\n"
    "L'Agent 1 détecte les manquants **avant** le lancement : "
    "on ne bloque plus la ligne en plein montage."
)
val2.markdown(
    "### ⏱️ Moins de chantiers en attente\n\n"
    "L'Agent 2 surveille le stock en continu : "
    "dès que les pièces arrivent, il donne le feu vert pour reprendre."
)
val3.markdown(
    "### 👁️ Visibilité sur chaque bogie\n\n"
    "Chaque OF a sa timeline complète : "
    "quand on pourra finir, quel est le risque, quelle est la consigne."
)

# =============================================================================
# État de santé de l'atelier — Graphiques
# =============================================================================

st.divider()
st.subheader("📈 État de santé de l'atelier")

col_g1, col_g2 = st.columns(2)

with col_g1:
    st.markdown("**Répartition des statuts**")
    all_statuses = ["Created", "Released", "PartiallyReleased", "Delayed", "ReadyToResume"]
    labels_fr = {
        "Created": "Non traités",
        "Released": "Lancés",
        "PartiallyReleased": "En partiel",
        "Delayed": "Différés",
        "ReadyToResume": "Prêts reprise",
    }
    status_counts = {labels_fr[s]: sum(1 for o in sim_orders.values() if o["status"] == s) for s in all_statuses}
    chart_data = pd.DataFrame([
        {"Statut": s, "Nombre": c}
        for s, c in status_counts.items() if c > 0
    ])
    if not chart_data.empty:
        st.bar_chart(chart_data, x="Statut", y="Nombre")
    else:
        st.info("Aucun OF traité.")

with col_g2:
    st.markdown("**Évolution : OF partiels vs bloqués (avant / avec solution)**")
    # Simulation avant/après pour illustrer la valeur
    comparison = pd.DataFrame({
        "Situation": ["Sans pilotage IA", "Avec pilotage IA"],
        "OF bloqués en ligne": [2, 0],
        "OF en attente gérée": [0, of_partial + of_delayed],
        "OF repris automatiquement": [0, of_resumed],
    })
    st.dataframe(comparison, use_container_width=True, hide_index=True)

    st.caption(
        "💡 *Sans l'IA, les OF manquants auraient été lancés et bloqués en pleine production. "
        "Avec le pilotage IA, ils sont identifiés en amont et repris au bon moment.*"
    )

# =============================================================================
# Top 5 OF à surveiller
# =============================================================================

st.divider()
st.subheader("🎯 Top OF sous tension — Ceux qui nécessitent votre attention")

watch_rows = []
for of_id, order in sim_orders.items():
    a1 = a1_outputs.get(of_id, {})
    a2 = a2_outputs.get(of_id, {})

    score = a1.get("global_risk_score", 0)
    risk = a1.get("risk_level", "—")
    eta = a2.get("overall_eta_days")

    # Ne montrer que les OF à risque ou non terminés
    if order["status"] in ("Released", "ReadyToResume") and score < 30:
        continue

    status_labels = {
        "Released": "🟢 Lancé",
        "PartiallyReleased": "🟠 Partiel",
        "Delayed": "🔴 Différé",
        "ReadyToResume": "✅ Prêt reprise",
    }

    watch_rows.append({
        "OF": order["orderNumber"],
        "Statut": status_labels.get(order["status"], "🔵 En attente"),
        "Risque": f"{'🔴' if risk == 'HIGH' else '🟠' if risk == 'MEDIUM' else '🟢' if risk == 'LOW' else '⚪'} {risk}",
        "Score": score,
        "Priorité": order["priority"],
        "Échéance": order["dueDate"][:10],
        "ETA reprise": f"{eta}j" if eta else "—",
        "Dernier agent": order.get("last_agent", "—"),
    })

if watch_rows:
    # Trier par score décroissant
    df_watch = pd.DataFrame(watch_rows).sort_values("Score", ascending=False)
    st.dataframe(df_watch, use_container_width=True, hide_index=True)
else:
    st.info("Aucun OF sous tension — tout est sous contrôle ✅")

# =============================================================================
# Tableau de bord complet (avec filtres)
# =============================================================================

st.divider()
st.subheader("📋 Tableau de bord complet")

col_f1, col_f2 = st.columns(2)
with col_f1:
    all_status_opts = ["Created", "Released", "PartiallyReleased", "Delayed", "ReadyToResume"]
    filter_status = st.multiselect("Filtrer par statut :", options=all_status_opts, default=all_status_opts)
with col_f2:
    filter_scenario = st.multiselect("Filtrer par scénario :", options=["OK", "Moyen", "Critique"], default=["OK", "Moyen", "Critique"])

rows = []
for of_id, order in sim_orders.items():
    if order["status"] not in filter_status:
        continue
    if order["scenario"] not in filter_scenario:
        continue

    a1 = a1_outputs.get(of_id, {})
    a2 = a2_outputs.get(of_id, {})

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
        "Prio reprise": a2.get("resume_priority", "—"),
        "ETA (j)": a2.get("overall_eta_days", "—"),
        "Dernier agent": order.get("last_agent", "—"),
    })

if rows:
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.info("Aucun OF ne correspond aux filtres.")

# =============================================================================
# Watchlist orchestrateur
# =============================================================================

st.divider()
st.subheader("👁️ Watchlist orchestrateur")
st.caption("OF actuellement sous surveillance par l'Agent 2.")

watchlist = st.session_state["watchlist"]
if watchlist:
    st.dataframe(pd.DataFrame(watchlist), use_container_width=True, hide_index=True)
else:
    st.info("Watchlist vide — aucun OF en surveillance.")

# =============================================================================
# Résumé textuel
# =============================================================================

st.divider()
st.subheader("📝 Résumé de la situation")

if sum(1 for o in sim_orders.values() if o["status"] == "Created") == total_of:
    st.markdown(
        "🔵 **Tous les OF sont en attente.** "
        "Lancez la simulation depuis le Cockpit Jour J pour voir les agents en action."
    )
elif of_released + of_resumed == total_of:
    st.markdown(
        "🟢 **Tous les OF sont lancés ou prêts à reprendre.** "
        "La production est en route, pas de blocage."
    )
else:
    lines = []
    if of_released:
        lines.append(f"🟢 **{of_released}** OF lancé(s) complètement")
    if of_partial:
        lines.append(f"🟠 **{of_partial}** OF en production partielle — à surveiller")
    if of_delayed:
        lines.append(f"🔴 **{of_delayed}** OF reporté(s) — composants critiques manquants")
    if of_resumed:
        lines.append(f"✅ **{of_resumed}** OF prêt(s) à reprendre — feu vert Agent 2")
    non_treated = sum(1 for o in sim_orders.values() if o["status"] == "Created")
    if non_treated:
        lines.append(f"🔵 **{non_treated}** OF non encore traité(s)")
    st.markdown("\n\n".join(lines))
