# """Page 3 — Vision Macro : Impact décisions Maestro & Sentinelle.

# KPIs avec méthodologie, jours restants central, timeline avec/sans IA,
# watchlist dynamique, santé atelier.
# """

# import streamlit as st
# import pandas as pd
# import sys, os
# from datetime import datetime, timezone, date

# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from data import build_seed_orders, ROUTING, WORK_HOURS_PER_DAY

# st.set_page_config(page_title="Vision Macro — Impact IA", page_icon="📊", layout="wide")

# TODAY = date(2026, 3, 12)
# NOW_UTC = datetime(2026, 3, 12, tzinfo=timezone.utc)

# # --- Init ---
# for key, default in [
#     ("orders", None), ("maestro_outputs", {}), ("sentinelle_outputs", {}),
#     ("watchlist", []), ("time_sim_results", {}), ("rescheduling_choices", {}),
# ]:
#     if key not in st.session_state:
#         st.session_state[key] = build_seed_orders() if key == "orders" else default

# orders = st.session_state["orders"]
# sim_orders = {k: v for k, v in orders.items() if k != "of-custom-001"}
# maestro_outs = st.session_state["maestro_outputs"]
# sentinelle_outs = st.session_state["sentinelle_outputs"]
# time_sim = st.session_state["time_sim_results"]


# def days_remaining_style(days_left):
#     if days_left >= 15:
#         return "🟢", "#2ecc71"
#     elif days_left >= 8:
#         return "🟠", "#f39c12"
#     else:
#         return "🔴", "#e74c3c"


# # =============================================================================
# # En-tête
# # =============================================================================

# st.markdown(
#     f"<div style='text-align:center; padding:10px; background:linear-gradient(90deg,#1a1a2e,#16213e); "
#     f"border-radius:10px; margin-bottom:12px;'>"
#     f"<span style='font-size:1.3em; color:white;'>📅 Aujourd'hui : <b>{TODAY.strftime('%d/%m/%Y')}</b></span>"
#     f"</div>",
#     unsafe_allow_html=True,
# )

# st.title("📊 Vision Macro : Impact des décisions Maestro & Sentinelle")
# st.caption(
#     "Maestro anticipe le film de production, Sentinelle valide dans le temps, "
#     "et l'humain décide. Résultat : on **pilote** les retards au lieu de les **subir**."
# )

# st.divider()

# # =============================================================================
# # KPIs — Jours restants central + méthodologie
# # =============================================================================

# total_of = len(sim_orders)
# of_analysed = sum(1 for k in sim_orders if k in maestro_outs)

# # Jours restants par OF
# days_by_of = {}
# for of_id, order in sim_orders.items():
#     due_dt = datetime.fromisoformat(order["dueDate"].replace("Z", "+00:00"))
#     days_by_of[of_id] = (due_dt - NOW_UTC).days

# worst_of_id = min(days_by_of, key=days_by_of.get) if days_by_of else None
# worst_days = days_by_of.get(worst_of_id, 99)
# worst_icon, worst_color = days_remaining_style(worst_days)

# # Calcul retards avec/sans IA
# delay_sans_ia_total = 0
# delay_avec_ia_total = 0
# penalties_sans_ia = 0
# penalties_avec_ia = 0

# for of_id, order in sim_orders.items():
#     m = maestro_outs.get(of_id, {})
#     s = sentinelle_outs.get(of_id, {})
#     ts = time_sim.get(of_id, {})

#     delay_sans_ia = m.get("estimated_delay_days", 0)
#     delay_sans_ia_total += delay_sans_ia
#     penalties_sans_ia += m.get("estimated_penalty_eur", 0)

#     # Avec IA : seule Sentinelle peut lever le risque
#     if s.get("warning_status") == "LEVE":
#         delay_avec_ia_total += 0
#         penalties_avec_ia += 0
#     elif s:
#         delay_avec_ia_total += s.get("updated_delay_days", 0)
#         penalties_avec_ia += s.get("updated_delay_days", 0) * 5000
#     elif m.get("recommended_action") == "LANCER_IMMEDIAT":
#         delay_avec_ia_total += 0
#     else:
#         delay_avec_ia_total += m.get("estimated_delay_days", 0)

# delay_evite = max(0, delay_sans_ia_total - delay_avec_ia_total)
# penalties_evitees = max(0, penalties_sans_ia - penalties_avec_ia)

# of_risk_leve = sum(
#     1 for of_id in sim_orders
#     if sentinelle_outs.get(of_id, {}).get("warning_status") == "LEVE"
# )

# of_at_risk = sum(
#     1 for of_id in sim_orders
#     if maestro_outs.get(of_id, {}).get("risk_level") in ("ORANGE", "ROUGE")
#     and sentinelle_outs.get(of_id, {}).get("warning_status") != "LEVE"
# )

# # ── Affichage KPIs ──
# kpi_cols = st.columns(5)

# with kpi_cols[0]:
#     st.markdown(
#         f"<div style='text-align:center; padding:16px; border:3px solid {worst_color}; "
#         f"border-radius:12px; background:{worst_color}22;'>"
#         f"<div style='font-size:2.5em; font-weight:bold; color:{worst_color};'>"
#         f"{worst_icon} {worst_days} j</div>"
#         f"<div style='font-size:0.9em;'>Jours restants (pire OF)</div>"
#         f"</div>",
#         unsafe_allow_html=True,
#     )
#     st.caption("Calcul : min(due date – aujourd'hui) sur tous les OF.")

# with kpi_cols[1]:
#     st.metric(
#         "OF analysés",
#         f"{of_analysed}/{total_of}",
#     )
#     st.caption("Calcul : nombre d'OF traités par Maestro / total.")

# with kpi_cols[2]:
#     st.metric(
#         "⏱️ Retard évité",
#         f"−{delay_evite} j" if delay_evite > 0 else "0 j",
#     )
#     st.caption("Calcul : retard sans IA − retard avec IA, en jours cumulés.")

# with kpi_cols[3]:
#     st.metric(
#         "💰 Pénalités évitées",
#         f"{penalties_evitees:,.0f} €" if penalties_evitees > 0 else "—",
#     )
#     st.caption("Calcul : pénalités sans IA − pénalités avec IA (SLA × retard).")

# with kpi_cols[4]:
#     st.metric(
#         "✅ Risques levés",
#         f"{of_risk_leve}",
#     )
#     st.caption("Calcul : OF dont le warning a été levé par Sentinelle/simulation.")


# # =============================================================================
# # Jours restants par OF — vue détaillée
# # =============================================================================

# st.divider()
# st.subheader("📅 Jours restants par OF")
# st.caption("Code couleur : 🟢 marge confortable (≥15j) | 🟠 marge faible (8-14j) | 🔴 quasi en retard (<8j)")

# days_rows = []
# for of_id, order in sim_orders.items():
#     dl = days_by_of[of_id]
#     dl_icon, dl_color = days_remaining_style(dl)

#     # Risque courant
#     ts = time_sim.get(of_id, {})
#     s = sentinelle_outs.get(of_id, {})
#     m = maestro_outs.get(of_id, {})

#     if ts.get("warning_status") == "LEVE" or s.get("warning_status") == "LEVE":
#         risk_label = "🟢 Risque levé"
#     elif ts.get("warning_status") == "CONFIRME" or s.get("warning_status") == "CONFIRME":
#         risk_label = "🔴 Risque confirmé"
#     elif m.get("risk_level"):
#         risk_icons = {"VERT": "🟢", "ORANGE": "🟠", "ROUGE": "🔴"}
#         risk_label = f"{risk_icons.get(m['risk_level'], '⚪')} {m['risk_level']}"
#     else:
#         risk_label = "⚪ Non analysé"

#     days_rows.append({
#         "OF": order["orderNumber"],
#         "Échéance": order["dueDate"][:10],
#         f"{dl_icon} J restants": dl,
#         "Risque": risk_label,
#         "Statut": order.get("status", "—"),
#     })

# st.dataframe(pd.DataFrame(days_rows), use_container_width=True, hide_index=True)


# # =============================================================================
# # Timeline comparée — Avec vs Sans IA
# # =============================================================================

# st.divider()
# st.subheader("📈 Timeline comparée — Avec vs Sans IA")

# if not maestro_outs:
#     st.info("Lancez Maestro depuis le Cockpit pour voir les comparaisons.")
# else:
#     timeline_rows = []
#     for of_id, order in sim_orders.items():
#         m = maestro_outs.get(of_id, {})
#         s = sentinelle_outs.get(of_id, {})
#         ts = time_sim.get(of_id, {})
#         if not m:
#             continue

#         due_date = order["dueDate"][:10]

#         # Sans IA
#         delay_sans = m.get("estimated_delay_days", 0)
#         end_sans = f"+{delay_sans}j retard" if delay_sans > 0 else "À l'heure"

#         # Avec IA
#         if ts.get("warning_status") == "LEVE" or s.get("warning_status") == "LEVE":
#             delay_avec = 0
#             end_avec = "✅ À l'heure (risque levé)"
#         elif s:
#             delay_avec = s.get("updated_delay_days", 0)
#             end_avec = f"+{delay_avec}j retard" if delay_avec > 0 else "✅ À l'heure"
#         elif m.get("recommended_action") == "LANCER_IMMEDIAT":
#             delay_avec = 0
#             end_avec = "✅ À l'heure"
#         else:
#             delay_avec = delay_sans
#             end_avec = f"+{delay_avec}j" if delay_avec > 0 else "—"

#         retard_evite_of = max(0, delay_sans - delay_avec)

#         timeline_rows.append({
#             "OF": order["orderNumber"],
#             "Échéance": due_date,
#             "Sans IA": end_sans,
#             "Avec IA": end_avec,
#             "Retard évité": f"{retard_evite_of}j" if retard_evite_of > 0 else "—",
#         })

#     if timeline_rows:
#         st.dataframe(pd.DataFrame(timeline_rows), use_container_width=True, hide_index=True)

#     # Bar chart
#     st.markdown("**Retard par OF : Sans IA vs Avec IA**")
#     chart_rows = []
#     for of_id, order in sim_orders.items():
#         m = maestro_outs.get(of_id, {})
#         s = sentinelle_outs.get(of_id, {})
#         ts = time_sim.get(of_id, {})
#         if not m:
#             continue

#         delay_sans = m.get("estimated_delay_days", 0)
#         if ts.get("warning_status") == "LEVE" or s.get("warning_status") == "LEVE":
#             delay_avec = 0
#         elif s:
#             delay_avec = s.get("updated_delay_days", 0)
#         else:
#             delay_avec = 0 if m.get("recommended_action") == "LANCER_IMMEDIAT" else delay_sans

#         chart_rows.append({
#             "OF": order["orderNumber"],
#             "Sans IA (jours retard)": delay_sans,
#             "Avec IA (jours retard)": delay_avec,
#         })

#     if chart_rows:
#         st.bar_chart(pd.DataFrame(chart_rows).set_index("OF"))


# # =============================================================================
# # Tableau de décisions
# # =============================================================================

# st.divider()
# st.subheader("📋 Tableau des décisions — La décision reste humaine")

# if not maestro_outs:
#     st.info("Aucune analyse disponible.")
# else:
#     dec_rows = []
#     for of_id, order in sim_orders.items():
#         m = maestro_outs.get(of_id, {})
#         s = sentinelle_outs.get(of_id, {})
#         ts = time_sim.get(of_id, {})
#         if not m:
#             continue

#         action_labels = {
#             "LANCER_IMMEDIAT": "✅ Lancer",
#             "LANCER_DECALE": "⚠️ Décaler",
#             "REPORTER_ET_REPLANIFIER": "🛑 Reporter",
#         }

#         # Fournisseurs
#         suppliers = [f"{sp['supplier_name']} ({sp['itemCode']})" for sp in m.get("supplier_order_plan", [])]
#         supplier_str = ", ".join(suppliers) if suppliers else "—"

#         # Emails
#         emails = m.get("simulated_emails", [])
#         email_statuses = []
#         for e in emails:
#             s_label = e.get("action_label", "⏳ En attente")
#             email_statuses.append(f"{e.get('to_name', '?')}: {s_label}")
#         email_str = " | ".join(email_statuses) if email_statuses else "—"

#         # Retard final
#         delay = m.get("estimated_delay_days", 0)
#         if ts.get("warning_status") == "LEVE" or s.get("warning_status") == "LEVE":
#             delay = 0

#         # Statut sentinelle / simulation
#         if ts.get("warning_status") == "LEVE":
#             sent_status = "✅ Risque levé (sim)"
#         elif ts.get("warning_status") == "CONFIRME":
#             sent_status = "🔴 Confirmé (sim)"
#         elif s.get("warning_status") == "LEVE":
#             sent_status = "✅ Risque levé"
#         elif s.get("warning_status") == "CONFIRME":
#             sent_status = "🔴 Confirmé"
#         elif s.get("warning_status"):
#             sent_status = "🔍 Surveillance"
#         else:
#             sent_status = "—"

#         # Replanification choisie
#         resch = m.get("chosen_rescheduling")
#         resch_str = resch["label"] if resch else "—"

#         dec_rows.append({
#             "OF": order["orderNumber"],
#             "Reco Maestro": action_labels.get(m.get("recommended_action"), "—"),
#             "Décision": action_labels.get(m.get("operator_decision"), "⏳"),
#             "Fournisseurs": supplier_str,
#             "Emails": email_str,
#             "Replanification": resch_str,
#             "Retard final": f"+{delay}j" if delay > 0 else "Aucun",
#             "Sentinelle": sent_status,
#         })

#     if dec_rows:
#         st.dataframe(pd.DataFrame(dec_rows), use_container_width=True, hide_index=True)

#     st.caption(
#         "💡 *La recommandation IA est une aide à la décision. "
#         "L'opérateur garde le dernier mot.*"
#     )


# # =============================================================================
# # Répartition des statuts
# # =============================================================================

# st.divider()
# st.subheader("📈 Santé de l'atelier")

# col_g1, col_g2 = st.columns(2)

# with col_g1:
#     st.markdown("**Répartition des risques**")
#     risk_counts = {"VERT": 0, "ORANGE": 0, "ROUGE": 0, "Non analysé": 0}
#     for of_id in sim_orders:
#         m = maestro_outs.get(of_id, {})
#         ts = time_sim.get(of_id, {})
#         s = sentinelle_outs.get(of_id, {})

#         if ts.get("warning_status") == "LEVE" or s.get("warning_status") == "LEVE":
#             risk_counts["VERT"] += 1
#         elif m.get("risk_level") in risk_counts:
#             risk_counts[m["risk_level"]] += 1
#         else:
#             risk_counts["Non analysé"] += 1

#     risk_df = pd.DataFrame([
#         {"Risque": "🟢 VERT", "Nombre": risk_counts["VERT"]},
#         {"Risque": "🟠 ORANGE", "Nombre": risk_counts["ORANGE"]},
#         {"Risque": "🔴 ROUGE", "Nombre": risk_counts["ROUGE"]},
#         {"Risque": "⚪ Non analysé", "Nombre": risk_counts["Non analysé"]},
#     ])
#     risk_df = risk_df[risk_df["Nombre"] > 0]
#     if not risk_df.empty:
#         st.bar_chart(risk_df.set_index("Risque"))

# with col_g2:
#     st.markdown("**Statut Sentinelle / Simulation**")
#     sent_counts = {"Risque levé": 0, "Risque confirmé": 0, "Surveillance": 0, "Non suivi": 0}
#     for of_id in sim_orders:
#         ts = time_sim.get(of_id, {})
#         s = sentinelle_outs.get(of_id, {})

#         if ts.get("warning_status") == "LEVE" or s.get("warning_status") == "LEVE":
#             sent_counts["Risque levé"] += 1
#         elif ts.get("warning_status") == "CONFIRME" or s.get("warning_status") == "CONFIRME":
#             sent_counts["Risque confirmé"] += 1
#         elif ts or s:
#             sent_counts["Surveillance"] += 1
#         else:
#             sent_counts["Non suivi"] += 1

#     sent_df = pd.DataFrame([
#         {"Statut": "✅ Risque levé", "Nombre": sent_counts["Risque levé"]},
#         {"Statut": "🔴 Risque confirmé", "Nombre": sent_counts["Risque confirmé"]},
#         {"Statut": "🔍 Surveillance", "Nombre": sent_counts["Surveillance"]},
#         {"Statut": "— Non suivi", "Nombre": sent_counts["Non suivi"]},
#     ])
#     sent_df = sent_df[sent_df["Nombre"] > 0]
#     if not sent_df.empty:
#         st.bar_chart(sent_df.set_index("Statut"))


# # =============================================================================
# # Valeur ajoutée
# # =============================================================================

# st.divider()

# val1, val2, val3 = st.columns(3)
# val1.markdown(
#     "### 🎼 Maestro anticipe\n\n"
#     "Avant de lancer, Maestro vérifie si la production "
#     "risque d'atteindre une étape critique avant l'arrivée "
#     "des pièces. On ne démarre plus à l'aveugle."
# )
# val2.markdown(
#     "### 🔭 Sentinelle valide\n\n"
#     "Sentinelle surveille en continu les livraisons. "
#     "Dès que les pièces arrivent, elle lève le warning "
#     "et passe l'OF au vert. Les KPI se recalculent."
# )
# val3.markdown(
#     "### 👤 L'humain décide\n\n"
#     "L'IA recommande, la décision finale reste humaine. "
#     "Le scénario « reprendre la production » est l'exception, "
#     "pas le centre : l'anticipation est la clé."
# )


# # =============================================================================
# # Résumé
# # =============================================================================

# st.divider()
# st.subheader("📝 Résumé de la situation")

# if not maestro_outs:
#     st.markdown("🔵 **Aucun OF analysé.** Lancez Maestro depuis le Cockpit.")
# else:
#     lines = []
#     of_vert = sum(
#         1 for k in sim_orders
#         if maestro_outs.get(k, {}).get("risk_level") == "VERT"
#         or time_sim.get(k, {}).get("warning_status") == "LEVE"
#         or sentinelle_outs.get(k, {}).get("warning_status") == "LEVE"
#     )
#     of_orange = sum(
#         1 for k in sim_orders
#         if maestro_outs.get(k, {}).get("risk_level") == "ORANGE"
#         and time_sim.get(k, {}).get("warning_status") != "LEVE"
#         and sentinelle_outs.get(k, {}).get("warning_status") != "LEVE"
#     )
#     of_rouge = sum(
#         1 for k in sim_orders
#         if maestro_outs.get(k, {}).get("risk_level") == "ROUGE"
#         and time_sim.get(k, {}).get("warning_status") != "LEVE"
#         and sentinelle_outs.get(k, {}).get("warning_status") != "LEVE"
#     )

#     if of_vert:
#         lines.append(f"🟢 **{of_vert}** OF sous contrôle")
#     if of_orange:
#         lines.append(f"🟠 **{of_orange}** OF à surveiller")
#     if of_rouge:
#         lines.append(f"🔴 **{of_rouge}** OF à risque")
#     if of_risk_leve:
#         lines.append(f"✅ **{of_risk_leve}** risque(s) levé(s)")
#     if delay_evite > 0:
#         lines.append(f"⏱️ **{delay_evite} jours** de retard évités")
#     if penalties_evitees > 0:
#         lines.append(f"💰 **{penalties_evitees:,.0f} €** de pénalités évitées")

#     st.markdown("\n\n".join(lines) if lines else "Données insuffisantes.")
"""
Page 3 — Vision Macro : Impact des décisions Maestro & Sentinelle

Vue portefeuille / atelier.
Cette page donne une lecture consolidée des effets des décisions prises :
- niveau global de risque sur les OF,
- marge avant échéance client,
- comparaison avec / sans pilotage IA,
- watchlist dynamique,
- état global de l’atelier.
"""

import streamlit as st
import pandas as pd
import sys, os
from datetime import datetime, timezone, date


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data import build_seed_orders, ROUTING, WORK_HOURS_PER_DAY


st.set_page_config(page_title="Vision Macro — Impact IA", page_icon="📊", layout="wide")


TODAY = date(2026, 3, 12)
NOW_UTC = datetime(2026, 3, 12, tzinfo=timezone.utc)


# --- Init ---
for key, default in [
    ("orders", None), ("maestro_outputs", {}), ("sentinelle_outputs", {}),
    ("watchlist", []), ("time_sim_results", {}), ("rescheduling_choices", {}),
]:
    if key not in st.session_state:
        st.session_state[key] = build_seed_orders() if key == "orders" else default


orders = st.session_state["orders"]
sim_orders = {k: v for k, v in orders.items() if k != "of-custom-001"}
maestro_outs = st.session_state["maestro_outputs"]
sentinelle_outs = st.session_state["sentinelle_outputs"]
time_sim = st.session_state["time_sim_results"]


def days_remaining_style(days_left):
    if days_left >= 15:
        return "🟢", "#2ecc71"
    elif days_left >= 8:
        return "🟠", "#f39c12"
    else:
        return "🔴", "#e74c3c"



# =============================================================================
# En-tête
# =============================================================================


st.markdown(
    f"<div style='text-align:center; padding:10px; background:linear-gradient(90deg,#1a1a2e,#16213e); "
    f"border-radius:10px; margin-bottom:12px;'>"
    f"<span style='font-size:1.3em; color:white;'>📅 Date du jour : <b>{TODAY.strftime('%d/%m/%Y')}</b></span>"
    f"</div>",
    unsafe_allow_html=True,
)


st.title("📊 Vision Macro : Impact des décisions Maestro & Sentinelle")
st.caption(
    "Cette vue donne une lecture consolidée du portefeuille d’OF : "
    "où se situent les tensions, quels retards peuvent être évités, "
    "et dans quelle mesure l’atelier reste sous contrôle grâce à l’anticipation et à la surveillance."
)


st.divider()


# =============================================================================
# KPIs — Jours restants central + méthodologie
# =============================================================================


total_of = len(sim_orders)
of_analysed = sum(1 for k in sim_orders if k in maestro_outs)


# Jours restants par OF
days_by_of = {}
for of_id, order in sim_orders.items():
    due_dt = datetime.fromisoformat(order["dueDate"].replace("Z", "+00:00"))
    days_by_of[of_id] = (due_dt - NOW_UTC).days


worst_of_id = min(days_by_of, key=days_by_of.get) if days_by_of else None
worst_days = days_by_of.get(worst_of_id, 99)
worst_icon, worst_color = days_remaining_style(worst_days)


# Calcul retards avec/sans IA
delay_sans_ia_total = 0
delay_avec_ia_total = 0
penalties_sans_ia = 0
penalties_avec_ia = 0


for of_id, order in sim_orders.items():
    m = maestro_outs.get(of_id, {})
    s = sentinelle_outs.get(of_id, {})
    ts = time_sim.get(of_id, {})

    delay_sans_ia = m.get("estimated_delay_days", 0)
    delay_sans_ia_total += delay_sans_ia
    penalties_sans_ia += m.get("estimated_penalty_eur", 0)

    # Avec IA : seule Sentinelle peut lever le risque
    if s.get("warning_status") == "LEVE":
        delay_avec_ia_total += 0
        penalties_avec_ia += 0
    elif s:
        delay_avec_ia_total += s.get("updated_delay_days", 0)
        penalties_avec_ia += s.get("updated_delay_days", 0) * 5000
    elif m.get("recommended_action") == "LANCER_IMMEDIAT":
        delay_avec_ia_total += 0
    else:
        delay_avec_ia_total += m.get("estimated_delay_days", 0)


delay_evite = max(0, delay_sans_ia_total - delay_avec_ia_total)
penalties_evitees = max(0, penalties_sans_ia - penalties_avec_ia)


of_risk_leve = sum(
    1 for of_id in sim_orders
    if sentinelle_outs.get(of_id, {}).get("warning_status") == "LEVE"
)

of_at_risk = sum(
    1 for of_id in sim_orders
    if maestro_outs.get(of_id, {}).get("risk_level") in ("ORANGE", "ROUGE")
    and sentinelle_outs.get(of_id, {}).get("warning_status") != "LEVE"
)


# ── Affichage KPIs ──
kpi_cols = st.columns(5)


with kpi_cols[0]:
    st.markdown(
        f"<div style='text-align:center; padding:16px; border:3px solid {worst_color}; "
        f"border-radius:12px; background:{worst_color}22;'>"
        f"<div style='font-size:2.5em; font-weight:bold; color:{worst_color};'>"
        f"{worst_icon} {worst_days} j</div>"
        f"<div style='font-size:0.9em;'>Marge restante la plus faible</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.caption("Méthode : minimum des jours restants avant échéance client sur l’ensemble des OF.")

with kpi_cols[1]:
    st.metric(
        "OF analysés",
        f"{of_analysed}/{total_of}",
    )
    st.caption("Méthode : nombre d’OF ayant déjà fait l’objet d’une analyse Maestro.")

with kpi_cols[2]:
    st.metric(
        "⏱️ Retard évité estimé",
        f"−{delay_evite} j" if delay_evite > 0 else "0 j",
    )
    st.caption("Méthode : retard cumulé sans pilotage IA moins retard cumulé avec pilotage IA.")

with kpi_cols[3]:
    st.metric(
        "💰 Pénalités évitées",
        f"{penalties_evitees:,.0f} €" if penalties_evitees > 0 else "—",
    )
    st.caption("Méthode : pénalités projetées sans IA moins pénalités projetées avec IA.")

with kpi_cols[4]:
    st.metric(
        "✅ Risques levés",
        f"{of_risk_leve}",
    )
    st.caption("Méthode : OF dont l’alerte a été levée par Sentinelle.")



# =============================================================================
# Jours restants par OF — vue détaillée
# =============================================================================


st.divider()
st.subheader("📅 Marge avant échéance par OF")
st.caption("Lecture : 🟢 marge confortable | 🟠 vigilance nécessaire | 🔴 marge très faible")


days_rows = []
for of_id, order in sim_orders.items():
    dl = days_by_of[of_id]
    dl_icon, dl_color = days_remaining_style(dl)

    # Risque courant
    ts = time_sim.get(of_id, {})
    s = sentinelle_outs.get(of_id, {})
    m = maestro_outs.get(of_id, {})

    if ts.get("warning_status") == "LEVE" or s.get("warning_status") == "LEVE":
        risk_label = "🟢 Risque levé"
    elif ts.get("warning_status") == "CONFIRME" or s.get("warning_status") == "CONFIRME":
        risk_label = "🔴 Risque confirmé"
    elif m.get("risk_level"):
        risk_icons = {"VERT": "🟢", "ORANGE": "🟠", "ROUGE": "🔴"}
        risk_label = f"{risk_icons.get(m['risk_level'], '⚪')} {m['risk_level']}"
    else:
        risk_label = "⚪ Non analysé"

    days_rows.append({
        "OF": order["orderNumber"],
        "Échéance": order["dueDate"][:10],
        f"{dl_icon} J restants": dl,
        "Risque": risk_label,
        "Statut": order.get("status", "—"),
    })


st.dataframe(pd.DataFrame(days_rows), use_container_width=True, hide_index=True)



# =============================================================================
# Timeline comparée — Avec vs Sans IA
# =============================================================================


st.divider()
st.subheader("📈 Comparaison macro — Avec pilotage IA vs sans pilotage IA")


if not maestro_outs:
    st.info("Lancez Maestro depuis le Cockpit pour alimenter cette comparaison.")
else:
    timeline_rows = []
    for of_id, order in sim_orders.items():
        m = maestro_outs.get(of_id, {})
        s = sentinelle_outs.get(of_id, {})
        ts = time_sim.get(of_id, {})
        if not m:
            continue

        due_date = order["dueDate"][:10]

        # Sans IA
        delay_sans = m.get("estimated_delay_days", 0)
        end_sans = f"+{delay_sans}j retard" if delay_sans > 0 else "À l’heure"

        # Avec IA
        if ts.get("warning_status") == "LEVE" or s.get("warning_status") == "LEVE":
            delay_avec = 0
            end_avec = "✅ À l’heure (risque levé)"
        elif s:
            delay_avec = s.get("updated_delay_days", 0)
            end_avec = f"+{delay_avec}j retard" if delay_avec > 0 else "✅ À l’heure"
        elif m.get("recommended_action") == "LANCER_IMMEDIAT":
            delay_avec = 0
            end_avec = "✅ À l’heure"
        else:
            delay_avec = delay_sans
            end_avec = f"+{delay_avec}j" if delay_avec > 0 else "—"

        retard_evite_of = max(0, delay_sans - delay_avec)

        timeline_rows.append({
            "OF": order["orderNumber"],
            "Échéance": due_date,
            "Sans pilotage IA": end_sans,
            "Avec pilotage IA": end_avec,
            "Retard évité": f"{retard_evite_of}j" if retard_evite_of > 0 else "—",
        })

    if timeline_rows:
        st.dataframe(pd.DataFrame(timeline_rows), use_container_width=True, hide_index=True)

    # Bar chart
    st.markdown("**Retard estimé par OF : comparaison directe**")
    chart_rows = []
    for of_id, order in sim_orders.items():
        m = maestro_outs.get(of_id, {})
        s = sentinelle_outs.get(of_id, {})
        ts = time_sim.get(of_id, {})
        if not m:
            continue

        delay_sans = m.get("estimated_delay_days", 0)
        if ts.get("warning_status") == "LEVE" or s.get("warning_status") == "LEVE":
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
        st.bar_chart(pd.DataFrame(chart_rows).set_index("OF"))



# =============================================================================
# Tableau de décisions
# =============================================================================


st.divider()
st.subheader("📋 Décisions prises et effets attendus")
st.caption("L’IA recommande, l’opérateur arbitre, et Sentinelle confirme ensuite l’évolution réelle du risque.")


if not maestro_outs:
    st.info("Aucune analyse disponible.")
else:
    dec_rows = []
    for of_id, order in sim_orders.items():
        m = maestro_outs.get(of_id, {})
        s = sentinelle_outs.get(of_id, {})
        ts = time_sim.get(of_id, {})
        if not m:
            continue

        action_labels = {
            "LANCER_IMMEDIAT": "✅ Lancer",
            "LANCER_DECALE": "⚠️ Décaler",
            "REPORTER_ET_REPLANIFIER": "🛑 Reporter",
        }

        # Fournisseurs
        suppliers = [f"{sp['supplier_name']} ({sp['itemCode']})" for sp in m.get("supplier_order_plan", [])]
        supplier_str = ", ".join(suppliers) if suppliers else "—"

        # Emails
        emails = m.get("simulated_emails", [])
        email_statuses = []
        for e in emails:
            s_label = e.get("action_label", "⏳ En attente")
            email_statuses.append(f"{e.get('to_name', '?')}: {s_label}")
        email_str = " | ".join(email_statuses) if email_statuses else "—"

        # Retard final
        delay = m.get("estimated_delay_days", 0)
        if ts.get("warning_status") == "LEVE" or s.get("warning_status") == "LEVE":
            delay = 0

        # Statut sentinelle / simulation
        if ts.get("warning_status") == "LEVE":
            sent_status = "✅ Risque levé (sim)"
        elif ts.get("warning_status") == "CONFIRME":
            sent_status = "🔴 Confirmé (sim)"
        elif s.get("warning_status") == "LEVE":
            sent_status = "✅ Risque levé"
        elif s.get("warning_status") == "CONFIRME":
            sent_status = "🔴 Confirmé"
        elif s.get("warning_status"):
            sent_status = "🔍 Surveillance"
        else:
            sent_status = "—"

        # Replanification choisie
        resch = m.get("chosen_rescheduling")
        resch_str = resch["label"] if resch else "—"

        dec_rows.append({
            "OF": order["orderNumber"],
            "Reco Maestro": action_labels.get(m.get("recommended_action"), "—"),
            "Décision opérateur": action_labels.get(m.get("operator_decision"), "⏳"),
            "Sécurisation fournisseur": supplier_str,
            "Actions email": email_str,
            "Replanification": resch_str,
            "Retard final": f"+{delay}j" if delay > 0 else "Aucun",
            "Statut Sentinelle": sent_status,
        })

    if dec_rows:
        st.dataframe(pd.DataFrame(dec_rows), use_container_width=True, hide_index=True)

    st.caption(
        "💡 *La recommandation IA reste une aide à la décision : la validation finale appartient à l’opérateur.*"
    )



# =============================================================================
# Répartition des statuts
# =============================================================================


st.divider()
st.subheader("📈 Santé globale de l’atelier")


col_g1, col_g2 = st.columns(2)


with col_g1:
    st.markdown("**Répartition des niveaux de risque**")
    risk_counts = {"VERT": 0, "ORANGE": 0, "ROUGE": 0, "Non analysé": 0}
    for of_id in sim_orders:
        m = maestro_outs.get(of_id, {})
        ts = time_sim.get(of_id, {})
        s = sentinelle_outs.get(of_id, {})

        if ts.get("warning_status") == "LEVE" or s.get("warning_status") == "LEVE":
            risk_counts["VERT"] += 1
        elif m.get("risk_level") in risk_counts:
            risk_counts[m["risk_level"]] += 1
        else:
            risk_counts["Non analysé"] += 1

    risk_df = pd.DataFrame([
        {"Risque": "🟢 VERT", "Nombre": risk_counts["VERT"]},
        {"Risque": "🟠 ORANGE", "Nombre": risk_counts["ORANGE"]},
        {"Risque": "🔴 ROUGE", "Nombre": risk_counts["ROUGE"]},
        {"Risque": "⚪ Non analysé", "Nombre": risk_counts["Non analysé"]},
    ])
    risk_df = risk_df[risk_df["Nombre"] > 0]
    if not risk_df.empty:
        st.bar_chart(risk_df.set_index("Risque"))


with col_g2:
    st.markdown("**Statut de surveillance Sentinelle**")
    sent_counts = {"Risque levé": 0, "Risque confirmé": 0, "Surveillance": 0, "Non suivi": 0}
    for of_id in sim_orders:
        ts = time_sim.get(of_id, {})
        s = sentinelle_outs.get(of_id, {})

        if ts.get("warning_status") == "LEVE" or s.get("warning_status") == "LEVE":
            sent_counts["Risque levé"] += 1
        elif ts.get("warning_status") == "CONFIRME" or s.get("warning_status") == "CONFIRME":
            sent_counts["Risque confirmé"] += 1
        elif ts or s:
            sent_counts["Surveillance"] += 1
        else:
            sent_counts["Non suivi"] += 1

    sent_df = pd.DataFrame([
        {"Statut": "✅ Risque levé", "Nombre": sent_counts["Risque levé"]},
        {"Statut": "🔴 Risque confirmé", "Nombre": sent_counts["Risque confirmé"]},
        {"Statut": "🔍 Surveillance", "Nombre": sent_counts["Surveillance"]},
        {"Statut": "— Non suivi", "Nombre": sent_counts["Non suivi"]},
    ])
    sent_df = sent_df[sent_df["Nombre"] > 0]
    if not sent_df.empty:
        st.bar_chart(sent_df.set_index("Statut"))



# =============================================================================
# Valeur ajoutée
# =============================================================================


st.divider()


val1, val2, val3 = st.columns(3)
val1.markdown(
    "### 🎼 Maestro anticipe\n\n"
    "Avant tout lancement, Maestro évalue si la production risque "
    "d’atteindre une étape critique avant l’arrivée des composants. "
    "On évite ainsi les démarrages non sécurisés."
)
val2.markdown(
    "### 🔭 Sentinelle confirme\n\n"
    "Sentinelle suit les OF sous surveillance, contrôle l’arrivée des pièces "
    "et met à jour le niveau de risque. Lorsqu’un risque est levé, "
    "la watchlist et les indicateurs sont réactualisés."
)
val3.markdown(
    "### 👤 L’humain arbitre\n\n"
    "L’IA prépare l’analyse et les options, mais la décision finale reste humaine. "
    "La reprise après blocage devient un cas d’exception ; "
    "l’objectif principal reste l’anticipation."
)



# =============================================================================
# Résumé
# =============================================================================


st.divider()
st.subheader("📝 Lecture synthétique de la situation")


if not maestro_outs:
    st.markdown("🔵 **Aucun OF n’a encore été analysé.** Lancez Maestro depuis le Cockpit.")
else:
    lines = []
    of_vert = sum(
        1 for k in sim_orders
        if maestro_outs.get(k, {}).get("risk_level") == "VERT"
        or time_sim.get(k, {}).get("warning_status") == "LEVE"
        or sentinelle_outs.get(k, {}).get("warning_status") == "LEVE"
    )
    of_orange = sum(
        1 for k in sim_orders
        if maestro_outs.get(k, {}).get("risk_level") == "ORANGE"
        and time_sim.get(k, {}).get("warning_status") != "LEVE"
        and sentinelle_outs.get(k, {}).get("warning_status") != "LEVE"
    )
    of_rouge = sum(
        1 for k in sim_orders
        if maestro_outs.get(k, {}).get("risk_level") == "ROUGE"
        and time_sim.get(k, {}).get("warning_status") != "LEVE"
        and sentinelle_outs.get(k, {}).get("warning_status") != "LEVE"
    )

    if of_vert:
        lines.append(f"🟢 **{of_vert}** OF sous contrôle")
    if of_orange:
        lines.append(f"🟠 **{of_orange}** OF sous vigilance")
    if of_rouge:
        lines.append(f"🔴 **{of_rouge}** OF en risque élevé")
    if of_risk_leve:
        lines.append(f"✅ **{of_risk_leve}** risque(s) déjà levé(s)")
    if delay_evite > 0:
        lines.append(f"⏱️ **{delay_evite} jours** de retard estimés évités")
    if penalties_evitees > 0:
        lines.append(f"💰 **{penalties_evitees:,.0f} €** de pénalités estimées évitées")

    st.markdown("\n\n".join(lines) if lines else "Données insuffisantes pour établir une lecture consolidée.")
