"""Page 3 — Vision Macro : Impact décisions Maestro & Sentinelle.

Objectif : montrer comment les recommandations d'IA changent le planning et le risque.
KPIs avec/sans IA, timeline comparée, tableau de décisions.
"""

import streamlit as st
import pandas as pd
import sys, os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data import build_seed_orders, ROUTING, WORK_HOURS_PER_DAY

st.set_page_config(page_title="Vision Macro — Impact IA", page_icon="📊", layout="wide")

# --- Init ---
if "orders" not in st.session_state:
    st.session_state["orders"] = build_seed_orders()
if "maestro_outputs" not in st.session_state:
    st.session_state["maestro_outputs"] = {}
if "sentinelle_outputs" not in st.session_state:
    st.session_state["sentinelle_outputs"] = {}
if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = []

orders = st.session_state["orders"]
sim_orders = {k: v for k, v in orders.items() if k != "of-custom-001"}
maestro_outs = st.session_state["maestro_outputs"]
sentinelle_outs = st.session_state["sentinelle_outputs"]

# =============================================================================
# Titre
# =============================================================================

st.title("📊 Vision Macro : Impact des décisions Maestro & Sentinelle")
st.markdown(
    "*À partir de la vision stock + étapes + fournisseurs, Maestro vous propose d'ajuster "
    "le film de production. Sentinelle vérifie que la réalité colle aux hypothèses. "
    "Résultat : vous **pilotez** vos retards, vous ne les **subissez** plus.*"
)

st.divider()

# =============================================================================
# KPIs — Avec vs Sans IA
# =============================================================================

st.subheader("🏆 OF planifiés avec Maestro vs sans IA")

total_of = len(sim_orders)
of_analysed = sum(1 for k in sim_orders if k in maestro_outs)

# Estimation de retard SANS IA : on suppose que tous les OF auraient été lancés immédiatement
# → les OF avec manquants auraient été bloqués en production
delay_sans_ia_total = 0
delay_avec_ia_total = 0
penalties_sans_ia = 0
penalties_avec_ia = 0

for of_id, order in sim_orders.items():
    m = maestro_outs.get(of_id, {})
    s = sentinelle_outs.get(of_id, {})

    # Sans IA : on lance aveuglément → retard = estimation Maestro
    delay_sans_ia = m.get("estimated_delay_days", 0)
    delay_sans_ia_total += delay_sans_ia
    penalties_sans_ia += m.get("estimated_penalty_eur", 0)

    # Avec IA : si Sentinelle a levé le risque, retard = 0 ; sinon retard actualisé
    if s.get("warning_status") == "LEVE":
        delay_avec_ia_total += 0
        penalties_avec_ia += 0
    elif s:
        delay_avec_ia_total += s.get("updated_delay_days", 0)
        # Estimer pénalités
        penalties_avec_ia += s.get("updated_delay_days", 0) * 5000
    elif m.get("recommended_action") == "LANCER_IMMEDIAT":
        delay_avec_ia_total += 0
    else:
        delay_avec_ia_total += m.get("estimated_delay_days", 0)

delay_evite = max(0, delay_sans_ia_total - delay_avec_ia_total)
penalties_evitees = max(0, penalties_sans_ia - penalties_avec_ia)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric(
    "OF analysés par Maestro",
    f"{of_analysed}/{total_of}",
    help="Nombre d'OF traités par Maestro",
)
kpi2.metric(
    "Écart retard (avec vs sans IA)",
    f"−{delay_evite} j" if delay_evite > 0 else "0 j",
    help="Jours de retard évités grâce aux recommandations",
)
kpi3.metric(
    "Pénalités évitées (estimé)",
    f"{penalties_evitees:,.0f} €" if penalties_evitees > 0 else "—",
    help="Estimation des pénalités évitées",
)

# OF où le risque a été levé par Sentinelle
of_risk_leve = sum(
    1 for of_id in sim_orders
    if sentinelle_outs.get(of_id, {}).get("warning_status") == "LEVE"
)
kpi4.metric(
    "Risques levés par Sentinelle",
    f"{of_risk_leve}",
    help="OF pour lesquels Sentinelle a confirmé que le risque était levé",
)

# =============================================================================
# Graphique : Timeline comparée — avec vs sans IA
# =============================================================================

st.divider()
st.subheader("📈 Timeline comparée par OF — Avec vs Sans IA")

if not maestro_outs:
    st.info("Lancez Maestro depuis le Cockpit pour voir les comparaisons.")
else:
    timeline_rows = []
    for of_id, order in sim_orders.items():
        m = maestro_outs.get(of_id, {})
        s = sentinelle_outs.get(of_id, {})
        if not m:
            continue

        due_date = order["dueDate"][:10]
        prod_days = m.get("estimated_production_days", 5)

        # Sans IA : lancement immédiat le 12/03, blocage si manquants
        launch_sans_ia = "2026-03-12"
        delay_sans = m.get("estimated_delay_days", 0)
        end_sans_ia = f"+{delay_sans}j retard" if delay_sans > 0 else "À l'heure"

        # Avec IA : lancement selon recommandation
        launch_avec_ia = m.get("recommended_launch_date") or "Reporter"
        if s and s.get("warning_status") == "LEVE":
            delay_avec = 0
            end_avec_ia = "✅ À l'heure (risque levé)"
        elif s:
            delay_avec = s.get("updated_delay_days", 0)
            end_avec_ia = f"+{delay_avec}j retard" if delay_avec > 0 else "À l'heure"
        else:
            delay_avec = m.get("estimated_delay_days", 0) if m.get("recommended_action") == "REPORTER_ET_REPLANIFIER" else 0
            end_avec_ia = f"+{delay_avec}j" if delay_avec > 0 else "✅ À l'heure"

        retard_evite = max(0, delay_sans - delay_avec)

        timeline_rows.append({
            "OF": order["orderNumber"],
            "Échéance": due_date,
            "Lancement sans IA": launch_sans_ia,
            "Résultat sans IA": end_sans_ia,
            "Lancement Maestro": launch_avec_ia,
            "Résultat avec IA": end_avec_ia,
            "Retard évité": f"{retard_evite} j" if retard_evite > 0 else "—",
        })

    if timeline_rows:
        st.dataframe(pd.DataFrame(timeline_rows), use_container_width=True, hide_index=True)

    # Graphique barres
    st.markdown("**Retard par OF : Sans IA vs Avec IA**")
    chart_rows = []
    for of_id, order in sim_orders.items():
        m = maestro_outs.get(of_id, {})
        s = sentinelle_outs.get(of_id, {})
        if not m:
            continue

        delay_sans = m.get("estimated_delay_days", 0)
        if s and s.get("warning_status") == "LEVE":
            delay_avec = 0
        elif s:
            delay_avec = s.get("updated_delay_days", 0)
        else:
            delay_avec = 0 if m.get("recommended_action") == "LANCER_IMMEDIAT" else delay_sans

        chart_rows.append({
            "OF": order["orderNumber"],
            "Sans IA (jours retard)": delay_sans,
            "Avec IA (jours retard)": delay_avec,
        })

    if chart_rows:
        chart_df = pd.DataFrame(chart_rows).set_index("OF")
        st.bar_chart(chart_df)


# =============================================================================
# Tableau de décisions
# =============================================================================

st.divider()
st.subheader("📋 Tableau des décisions — La décision reste humaine")

if not maestro_outs:
    st.info("Aucune analyse disponible.")
else:
    dec_rows = []
    for of_id, order in sim_orders.items():
        m = maestro_outs.get(of_id, {})
        s = sentinelle_outs.get(of_id, {})
        if not m:
            continue

        action_labels = {
            "LANCER_IMMEDIAT": "✅ Lancer",
            "LANCER_DECALE": "⚠️ Décaler",
            "REPORTER_ET_REPLANIFIER": "🛑 Reporter",
        }

        # Recommandations fournisseurs
        suppliers = []
        for sp in m.get("supplier_order_plan", []):
            suppliers.append(f"{sp['supplier_name']} ({sp['itemCode']})")
        supplier_str = ", ".join(suppliers) if suppliers else "—"

        # Impact
        delay = m.get("estimated_delay_days", 0)
        if s and s.get("warning_status") == "LEVE":
            delay = 0

        dec_rows.append({
            "OF": order["orderNumber"],
            "Reco Maestro": action_labels.get(m.get("recommended_action"), "—"),
            "Décision opérateur": action_labels.get(m.get("operator_decision"), "⏳ En attente"),
            "Fournisseurs": supplier_str,
            "Retard final": f"+{delay} j" if delay > 0 else "Aucun",
            "Status Sentinelle": {
                "LEVE": "✅ Levé",
                "CONFIRME": "🔴 Confirmé",
                "EN_SURVEILLANCE": "🔍 Surveillance",
            }.get(s.get("warning_status"), "—"),
            "Impact durée": f"{m.get('estimated_production_days', '?')} j prod",
        })

    if dec_rows:
        st.dataframe(pd.DataFrame(dec_rows), use_container_width=True, hide_index=True)

    st.caption(
        "💡 *La recommandation IA est un aide à la décision. "
        "L'opérateur garde le dernier mot sur le lancement ou le report.*"
    )


# =============================================================================
# Répartition des statuts
# =============================================================================

st.divider()
st.subheader("📈 Santé de l'atelier")

col_g1, col_g2 = st.columns(2)

with col_g1:
    st.markdown("**Répartition des risques Maestro**")
    risk_counts = {"VERT": 0, "ORANGE": 0, "ROUGE": 0, "Non analysé": 0}
    for of_id in sim_orders:
        m = maestro_outs.get(of_id, {})
        rl = m.get("risk_level")
        if rl in risk_counts:
            risk_counts[rl] += 1
        else:
            risk_counts["Non analysé"] += 1

    risk_df = pd.DataFrame([
        {"Risque": f"🟢 VERT", "Nombre": risk_counts["VERT"]},
        {"Risque": f"🟠 ORANGE", "Nombre": risk_counts["ORANGE"]},
        {"Risque": f"🔴 ROUGE", "Nombre": risk_counts["ROUGE"]},
        {"Risque": f"⚪ Non analysé", "Nombre": risk_counts["Non analysé"]},
    ])
    risk_df = risk_df[risk_df["Nombre"] > 0]
    if not risk_df.empty:
        st.bar_chart(risk_df.set_index("Risque"))
    else:
        st.info("Aucun OF analysé.")

with col_g2:
    st.markdown("**Statut Sentinelle**")
    sent_counts = {"LEVE": 0, "CONFIRME": 0, "EN_SURVEILLANCE": 0, "Non suivi": 0}
    for of_id in sim_orders:
        s = sentinelle_outs.get(of_id, {})
        ws = s.get("warning_status")
        if ws in sent_counts:
            sent_counts[ws] += 1
        else:
            sent_counts["Non suivi"] += 1

    sent_df = pd.DataFrame([
        {"Statut": "✅ Risque levé", "Nombre": sent_counts["LEVE"]},
        {"Statut": "🔴 Risque confirmé", "Nombre": sent_counts["CONFIRME"]},
        {"Statut": "🔍 Surveillance", "Nombre": sent_counts["EN_SURVEILLANCE"]},
        {"Statut": "— Non suivi", "Nombre": sent_counts["Non suivi"]},
    ])
    sent_df = sent_df[sent_df["Nombre"] > 0]
    if not sent_df.empty:
        st.bar_chart(sent_df.set_index("Statut"))
    else:
        st.info("Aucun suivi Sentinelle.")


# =============================================================================
# Encadré valeur
# =============================================================================

st.divider()

val1, val2, val3 = st.columns(3)
val1.markdown(
    "### 🎼 Maestro anticipe\n\n"
    "Avant de lancer, Maestro vérifie si la production "
    "risque d'atteindre une étape critique avant l'arrivée "
    "des pièces. Résultat : on ne démarre plus à l'aveugle."
)
val2.markdown(
    "### 🔭 Sentinelle valide\n\n"
    "Sentinelle surveille en continu les livraisons et "
    "l'avancement production. Dès que les pièces arrivent, "
    "elle lève le warning et confirme le planning."
)
val3.markdown(
    "### 👤 L'humain décide\n\n"
    "L'IA recommande, la décision finale reste humaine. "
    "Le responsable de production garde le dernier mot "
    "sur le lancement, le décalage ou le report."
)


# =============================================================================
# Résumé
# =============================================================================

st.divider()
st.subheader("📝 Résumé de la situation")

if not maestro_outs:
    st.markdown(
        "🔵 **Aucun OF analysé.** "
        "Lancez Maestro depuis le Cockpit pour voir les résultats."
    )
else:
    lines = []
    of_vert = sum(1 for k in sim_orders if maestro_outs.get(k, {}).get("risk_level") == "VERT")
    of_orange = sum(1 for k in sim_orders if maestro_outs.get(k, {}).get("risk_level") == "ORANGE")
    of_rouge = sum(1 for k in sim_orders if maestro_outs.get(k, {}).get("risk_level") == "ROUGE")

    if of_vert:
        lines.append(f"🟢 **{of_vert}** OF sans risque — lancement immédiat")
    if of_orange:
        lines.append(f"🟠 **{of_orange}** OF à surveiller — lancement décalé recommandé")
    if of_rouge:
        lines.append(f"🔴 **{of_rouge}** OF à risque — report recommandé")
    if of_risk_leve:
        lines.append(f"✅ **{of_risk_leve}** risque(s) levé(s) par Sentinelle")

    if delay_evite > 0:
        lines.append(f"⏱️ **{delay_evite} jours** de retard évités grâce aux recommandations IA")
    if penalties_evitees > 0:
        lines.append(f"💰 **{penalties_evitees:,.0f} €** de pénalités évitées (estimé)")

    st.markdown("\n\n".join(lines) if lines else "Données insuffisantes pour un résumé.")
