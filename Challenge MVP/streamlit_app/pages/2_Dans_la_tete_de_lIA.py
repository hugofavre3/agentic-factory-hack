# # """Page 2 — Maestro & Sentinelle (Décisions et impacts).

# # Production film explicite, timing pièces vs étapes, status emails fournisseur,
# # créneaux de replanification, comparaison avec/sans IA.
# # """

# # import streamlit as st
# # import pandas as pd
# # import sys, os
# # from datetime import datetime, timezone, date

# # sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# # from data import (
# #     build_seed_orders, ROUTING, WORK_HOURS_PER_DAY, SUPPLIERS_DATA,
# #     _check_availability, _find_cutoff, _find_last_doable,
# #     build_live_context_maestro, build_live_context_sentinelle,
# #     MAESTRO_SYSTEM_PROMPT, SENTINELLE_SYSTEM_PROMPT,
# # )

# # st.set_page_config(page_title="Maestro & Sentinelle", page_icon="🧠", layout="wide")

# # TODAY = date(2026, 3, 12)
# # NOW_UTC = datetime(2026, 3, 12, tzinfo=timezone.utc)

# # # --- Init ---
# # for key, default in [
# #     ("orders", None), ("maestro_outputs", {}), ("sentinelle_outputs", {}),
# #     ("watchlist", []), ("time_sim_results", {}), ("rescheduling_choices", {}),
# # ]:
# #     if key not in st.session_state:
# #         st.session_state[key] = build_seed_orders() if key == "orders" else default

# # orders = st.session_state["orders"]
# # sim_orders = {k: v for k, v in orders.items() if k != "of-custom-001"}


# # def days_remaining_color(days_left):
# #     if days_left >= 15:
# #         return "🟢", "#2ecc71"
# #     elif days_left >= 8:
# #         return "🟠", "#f39c12"
# #     else:
# #         return "🔴", "#e74c3c"


# # # =============================================================================
# # # En-tête
# # # =============================================================================

# # st.markdown(
# #     f"<div style='text-align:center; padding:10px; background:linear-gradient(90deg,#1a1a2e,#16213e); "
# #     f"border-radius:10px; margin-bottom:12px;'>"
# #     f"<span style='font-size:1.3em; color:white;'>📅 Aujourd'hui : <b>{TODAY.strftime('%d/%m/%Y')}</b></span>"
# #     f"</div>",
# #     unsafe_allow_html=True,
# # )

# # st.title("🧠 Maestro & Sentinelle — Décisions et impacts")
# # st.caption(
# #     "Comprendre le raisonnement de l'IA : pourquoi ce créneau, "
# #     "comment le film de production se déroule par rapport aux arrivées pièces."
# # )

# # st.divider()

# # # =============================================================================
# # # Onglets
# # # =============================================================================

# # tab1, tab2 = st.tabs([
# #     "🎼 Maestro — Stratégie de lancement",
# #     "🔭 Sentinelle — Surveillance et actualisation",
# # ])

# # # =============================================================================
# # # Onglet Maestro
# # # =============================================================================

# # with tab1:
# #     st.markdown("### 🎼 Maestro : Film de production et stratégie")
# #     st.caption(
# #         "Maestro croise étapes de production, temps de traversée, stock et délais fournisseurs. "
# #         "Question clé : *\"Si je lance, la production atteindra-t-elle l'étape critique avant l'arrivée des pièces ?\"*"
# #     )

# #     m_outputs = st.session_state["maestro_outputs"]

# #     if not m_outputs:
# #         st.info("Aucune analyse Maestro. Allez dans le **Cockpit** et lancez Maestro sur un OF.")
# #     else:
# #         m_keys = [k for k in m_outputs if k in orders]
# #         selected_of = st.selectbox(
# #             "Sélectionner un OF :",
# #             options=m_keys,
# #             format_func=lambda x: f"{orders[x]['orderNumber']} — {orders[x]['scenario_label']}",
# #             key="m_select",
# #         )

# #         output = m_outputs[selected_of]
# #         order = orders[selected_of]

# #         # ── Jours restants ──
# #         due_dt = datetime.fromisoformat(order["dueDate"].replace("Z", "+00:00"))
# #         days_left = (due_dt - NOW_UTC).days
# #         dl_icon, dl_color = days_remaining_color(days_left)

# #         col_dl, col_risk, col_action = st.columns(3)
# #         with col_dl:
# #             st.markdown(
# #                 f"<div style='text-align:center; padding:12px; border:3px solid {dl_color}; "
# #                 f"border-radius:10px;'>"
# #                 f"<div style='font-size:2.2em; font-weight:bold; color:{dl_color};'>"
# #                 f"{dl_icon} {days_left} j</div>"
# #                 f"<div>avant due date</div></div>",
# #                 unsafe_allow_html=True,
# #             )
# #         with col_risk:
# #             risk = output["risk_level"]
# #             score = output["global_risk_score"]
# #             risk_icons = {"VERT": "🟢", "ORANGE": "🟠", "ROUGE": "🔴"}
# #             st.metric(f"{risk_icons.get(risk, '⚪')} Risque", f"{risk} ({score}/100)")
# #         with col_action:
# #             action = output.get("operator_decision") or output.get("recommended_action", "?")
# #             action_labels = {
# #                 "LANCER_IMMEDIAT": "✅ Lancer immédiatement",
# #                 "LANCER_DECALE": "⚠️ Lancer en décalé",
# #                 "REPORTER_ET_REPLANIFIER": "🛑 Reporter",
# #             }
# #             st.metric("Décision", action_labels.get(action, action))

# #         if output.get("operator_decision"):
# #             st.success(f"**Consigne atelier** : {output.get('instruction', '—')}")
# #         else:
# #             st.warning("⏳ En attente de décision opérateur.")

# #         # ── Impact planning ──
# #         st.markdown("---")
# #         st.markdown("#### ⏱️ Impact sur le planning")

# #         ic1, ic2, ic3, ic4 = st.columns(4)
# #         ic1.metric("Prob. blocage", f"{output['probabilite_blocage_pct']}%")
# #         ic1.caption("Calcul : probabilité que la prod atteigne l'étape avant les pièces.")
# #         ic2.metric("Retard estimé", f"{output['estimated_delay_days']} j")
# #         ic2.caption("Calcul : Delta ETA pièces – progression prod.")
# #         ic3.metric("Pénalités", f"{output['estimated_penalty_eur']:,.0f} €")
# #         ic3.caption("Calcul : retard × pénalité/jour SLA.")
# #         ic4.metric("Durée prod.", f"{output.get('estimated_production_days', '?')} j")
# #         ic4.caption("Calcul : somme des durées d'étapes / 8h par jour.")

# #         if output.get("sla_impact"):
# #             st.caption(f"📋 **SLA** : {output['sla_impact']}")

# #         # ──────────────────────────────────────────────────────
# #         # FILM DE PRODUCTION EXPLICITE
# #         # ──────────────────────────────────────────────────────
# #         st.markdown("---")
# #         st.markdown("#### 🎬 Film de production — Timeline explicite")
# #         st.caption(
# #             "Chaque étape montre sa durée propre et le cumul depuis le début. "
# #             "Les warnings sont affichés sous l'étape avec l'analyse temporelle."
# #         )

# #         etape = output.get("etape_a_risque")
# #         missing_codes = {mc["itemCode"] for mc in output.get("missing_components", [])}

# #         # ETA fournisseur par composant
# #         supplier_etas = {}
# #         for plan in output.get("supplier_order_plan", []):
# #             supplier_etas[plan["itemCode"]] = plan["estimated_lead_days"]

# #         # Décalage lancement
# #         launch_offset = 0
# #         if output.get("recommended_action") == "LANCER_DECALE" and output.get("recommended_launch_date"):
# #             try:
# #                 ld = datetime.strptime(output["recommended_launch_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
# #                 launch_offset = (ld - NOW_UTC).days
# #             except (ValueError, TypeError):
# #                 launch_offset = 1

# #         for op in ROUTING:
# #             dur_days = round(op["duration_hours"] / WORK_HOURS_PER_DAY, 1)
# #             cumul_days = round(op["cumulative_end_hours"] / WORK_HOURS_PER_DAY, 1)
# #             reach_days = round(op["cumulative_start_hours"] / WORK_HOURS_PER_DAY, 1)

# #             blocked_items = set(op.get("requiredComponents", [])) & missing_codes
# #             is_risk = etape and op["operationId"] == etape["operationId"]

# #             icon = "🔴" if is_risk else ("🟠" if blocked_items else "🟢")
# #             comps = ", ".join(op.get("requiredComponents", [])) or "—"

# #             st.markdown(
# #                 f"{icon} **{op['operationId']}** — {op['description']}  \n"
# #                 f"&nbsp;&nbsp;&nbsp;&nbsp;⏱️ Durée : **{dur_days}j** pour cette étape "
# #                 f"| Cumul depuis début : **{cumul_days}j** "
# #                 f"| Composants : {comps}"
# #             )

# #             if blocked_items:
# #                 for item in blocked_items:
# #                     eta = supplier_etas.get(item)
# #                     eff_reach = reach_days + launch_offset
# #                     if eta is not None:
# #                         if eta <= eff_reach:
# #                             st.markdown(
# #                                 f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
# #                                 f"✅ {item} : ETA J+{eta} ≤ étape J+{eff_reach:.0f} → OK"
# #                             )
# #                         else:
# #                             st.markdown(
# #                                 f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
# #                                 f"🔴 **Risque de manquer `{item}` ici** — "
# #                                 f"ETA J+{eta} > étape J+{eff_reach:.0f}"
# #                             )
# #                     else:
# #                         st.markdown(
# #                             f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
# #                             f"🟠 {item} manquant — pas de plan fournisseur"
# #                         )

# #         # Texte récapitulatif temporel
# #         if etape and output.get("supplier_order_plan"):
# #             relevant = [p for p in output["supplier_order_plan"]
# #                         if p["itemCode"] == etape.get("composant_manquant")]
# #             if relevant:
# #                 eta = relevant[0]["estimated_lead_days"]
# #                 reach = etape["time_to_reach_days"]
# #                 st.markdown("---")

# #                 if output.get("recommended_action") == "LANCER_DECALE":
# #                     new_reach = reach + launch_offset
# #                     st.info(
# #                         f"📐 Si on lance **maintenant**, on atteindra {etape['operationId']} "
# #                         f"dans **{reach}j**. ETA pièces : J+{eta} → risque de blocage.\n\n"
# #                         f"💡 **Nouveau lancement recommandé** : J+{launch_offset} → "
# #                         f"{etape['operationId']} atteint à J+{new_reach:.0f}, "
# #                         f"ETA pièces J+{eta} → risque réduit."
# #                     )
# #                 elif eta > reach:
# #                     st.error(
# #                         f"📐 Si on lance maintenant, on atteindra {etape['operationId']} "
# #                         f"dans **{reach}j**. ETA pièces : J+{eta} → **risque de blocage élevé**."
# #                     )
# #                 else:
# #                     st.success(
# #                         f"📐 Pièces arrivent J+{eta}, étape atteinte J+{reach} → OK."
# #                     )

# #         # ── Production vs Arrivée chart ──
# #         st.markdown("---")
# #         st.markdown("#### 📈 Production vs Arrivée pièces")

# #         if etape and output.get("supplier_order_plan"):
# #             relevant_plan = [p for p in output["supplier_order_plan"]
# #                              if p["itemCode"] == etape["composant_manquant"]]
# #             sup_eta_days = relevant_plan[0]["estimated_lead_days"] if relevant_plan else None

# #             steps_data = []
# #             for op in ROUTING:
# #                 day = round(op["cumulative_start_hours"] / WORK_HOURS_PER_DAY, 1)
# #                 steps_data.append({
# #                     "Étape": op["operationId"],
# #                     "Production (jour)": day,
# #                 })

# #             col_chart, col_legend = st.columns([3, 1])
# #             with col_chart:
# #                 chart_df = pd.DataFrame(steps_data)
# #                 chart_df["Production"] = chart_df["Production (jour)"]
# #                 if sup_eta_days:
# #                     chart_df["ETA pièce"] = sup_eta_days
# #                     st.line_chart(chart_df.set_index("Étape")[["Production", "ETA pièce"]])
# #                 else:
# #                     st.line_chart(chart_df.set_index("Étape")[["Production"]])

# #             with col_legend:
# #                 st.markdown("**Légende**")
# #                 st.markdown("📈 Production (jours)")
# #                 if sup_eta_days:
# #                     st.markdown(f"📦 ETA {etape['composant_manquant']} : J+{sup_eta_days}")
# #                 st.markdown("⚠️ Croisement = zone de risque")
# #         elif not etape:
# #             st.success("✅ Aucune étape à risque — stock complet.")

# #         # ── Créneaux reprogrammation ──
# #         opts = output.get("rescheduling_options", [])
# #         if opts:
# #             st.markdown("---")
# #             st.markdown("#### 🔄 Créneaux de reprogrammation")
# #             for i, opt in enumerate(opts):
# #                 with st.expander(f"**Option {i+1}** : {opt['label']}", expanded=(i == 0)):
# #                     st.markdown(f"- Lancement : **{opt['launch_date']}**")
# #                     st.markdown(f"- Fin estimée : {opt['estimated_completion']}")
# #                     st.markdown(f"- Retard client : **+{opt['delay_client_days']}j**")
# #                     st.markdown(f"- Pénalités : {opt['penalty_eur']:,.0f} €")
# #                     st.markdown(f"- *{opt['comment']}*")
# #                     if opt.get("delay_client_days", 0) > 0:
# #                         st.warning(f"⚠️ Tensions possibles sur d'autres OF si charge en pointe.")

# #             chosen = output.get("chosen_rescheduling")
# #             if chosen:
# #                 st.success(f"✅ Décision enregistrée : **{chosen['label']}** — retard +{chosen['delay_client_days']}j")

# #         # ── Emails fournisseur (avec statut validation) ──
# #         emails = output.get("simulated_emails", [])
# #         if emails:
# #             st.markdown("---")
# #             st.markdown("#### 📧 Notifications fournisseur")
# #             for email in emails:
# #                 status = email.get("status")
# #                 status_label = email.get("action_label", "⏳ En attente de validation")
# #                 st.markdown(f"**{email['to_name']}** — {email['subject']} → {status_label}")
# #                 with st.expander(f"📨 Voir le message"):
# #                     st.markdown(f"**À** : {email['to_name']} <{email['to']}>")
# #                     st.markdown(f"**Objet** : {email['subject']}")
# #                     st.divider()
# #                     st.text(email["body"])

# #         # ── Stock & facteurs ──
# #         st.markdown("---")
# #         st.markdown("#### 📋 Pourquoi ce choix ?")

# #         st.markdown("**Stock actuel pour cet OF**")
# #         stock_rows = []
# #         for comp in order["components"]:
# #             needed = comp["qtyPerUnit"] * order["quantity"]
# #             avail = order["stock"].get(comp["itemCode"], 0)
# #             step = "—"
# #             for op in ROUTING:
# #                 if comp["itemCode"] in op.get("requiredComponents", []):
# #                     step = op["operationId"]
# #                     break
# #             stock_rows.append({
# #                 "Composant": comp["itemCode"],
# #                 "Besoin": needed,
# #                 "Dispo": avail,
# #                 "Étape": step,
# #                 "État": "✅" if avail >= needed else "❌",
# #                 "Critique": "🔴" if comp.get("isCritical") else "",
# #             })
# #         st.dataframe(pd.DataFrame(stock_rows), use_container_width=True, hide_index=True)

# #         if output.get("risk_factors"):
# #             st.markdown("**Facteurs de risque**")
# #             st.dataframe(pd.DataFrame(output["risk_factors"]), use_container_width=True, hide_index=True)

# #         if output.get("reasoning"):
# #             with st.expander("💬 Explication détaillée"):
# #                 st.write(output["reasoning"])

# #         # ── Prompts et JSON ──
# #         _missing = _check_availability(order["components"], order["quantity"], order["stock"])
# #         _cutoff = _find_cutoff(ROUTING, _missing)
# #         _last = _find_last_doable(ROUTING, _cutoff)
# #         _prompt = build_live_context_maestro(order, order["stock"], _missing, _cutoff, _last)

# #         with st.expander("📝 Prompt envoyé à Maestro"):
# #             st.code(MAESTRO_SYSTEM_PROMPT, language="markdown")
# #             st.code(_prompt, language="markdown")
# #         with st.expander("🔧 JSON technique"):
# #             st.json(output)


# # # =============================================================================
# # # Onglet Sentinelle
# # # =============================================================================

# # with tab2:
# #     st.markdown("### 🔭 Sentinelle : Surveillance et actualisation")
# #     st.caption(
# #         "Sentinelle surveille en continu les livraisons, met à jour le risque, "
# #         "et lève les warnings dès que les pièces arrivent."
# #     )

# #     s_outputs = st.session_state["sentinelle_outputs"]
# #     time_sim = st.session_state["time_sim_results"]

# #     # Sentinelle = source de vérité pour le risque
# #     # time_sim = info de progression production uniquement
# #     all_outputs = {}
# #     for k, v in s_outputs.items():
# #         all_outputs[k] = ("sentinelle", v)
# #     # Ajouter les OF qui n'ont que de la simulation (pas encore de sentinelle)
# #     for k, v in time_sim.items():
# #         if k not in all_outputs:
# #             all_outputs[k] = ("simulation", v)

# #     if not all_outputs:
# #         st.info("Aucune analyse Sentinelle ou simulation temporelle.")
# #     else:
# #         s_keys = [k for k in all_outputs if k in orders]
# #         selected_of2 = st.selectbox(
# #             "Sélectionner un OF :",
# #             options=s_keys,
# #             format_func=lambda x: f"{orders[x]['orderNumber']} — {orders[x]['scenario_label']}",
# #             key="s_select",
# #         )

# #         source_type, output2 = all_outputs[selected_of2]
# #         order2 = orders[selected_of2]
# #         m_ref = st.session_state["maestro_outputs"].get(selected_of2, {})

# #         # ── Jours restants ──
# #         due_dt2 = datetime.fromisoformat(order2["dueDate"].replace("Z", "+00:00"))
# #         days_left2 = (due_dt2 - NOW_UTC).days
# #         dl_icon2, dl_color2 = days_remaining_color(days_left2)

# #         st.markdown(
# #             f"<div style='text-align:center; padding:8px; border:2px solid {dl_color2}; "
# #             f"border-radius:8px; margin-bottom:12px;'>"
# #             f"<span style='font-size:1.5em; font-weight:bold; color:{dl_color2};'>"
# #             f"{dl_icon2} {days_left2} jours restants</span>"
# #             f"<span> avant due date client</span></div>",
# #             unsafe_allow_html=True,
# #         )

# #         # ── Évolution du risque ──
# #         st.markdown("---")
# #         st.markdown("#### 📊 Évolution du risque")

# #         if source_type == "simulation":
# #             # Simulation temporelle (avancement seul, pas de constat pièces)
# #             ev_col1, ev_col2, ev_col3 = st.columns(3)
# #             risk_icons = {"VERT": "🟢", "ORANGE": "🟠", "ROUGE": "🔴"}
# #             init_risk = m_ref.get("risk_level", "?")

# #             ev_col1.metric("Risque initial (Maestro)", f"{risk_icons.get(init_risk, '⚪')} {init_risk}")
# #             ev_col2.metric("Jour simulé", f"J+{output2.get('days_advanced', 0)}")
# #             if output2.get("days_remaining_to_risk") is not None:
# #                 ev_col3.metric("Proximité risque", f"{output2['days_remaining_to_risk']}j")
# #             else:
# #                 ev_col3.metric("Proximité risque", "—")

# #             if output2.get("blocked"):
# #                 st.error(f"🔴 {output2['message']}")
# #             elif output2.get("missing_components"):
# #                 st.warning(f"🟠 {output2['message']}")
# #             else:
# #                 st.success(f"🟢 {output2['message']}")

# #             st.info("💡 **Lancez Sentinelle** pour vérifier si les pièces sont arrivées.")

# #             # Timeline de progression
# #             st.markdown("---")
# #             st.markdown("#### 🎬 Progression production simulée")
# #             hours = output2.get("hours_elapsed", 0)
# #             sim_cols = st.columns(len(ROUTING))
# #             for i, (col, op) in enumerate(zip(sim_cols, ROUTING)):
# #                 if hours >= op["cumulative_end_hours"]:
# #                     col.markdown(f"✅ **{op['operationId'][:4]}**")
# #                     col.caption("Terminé")
# #                 elif hours >= op["cumulative_start_hours"]:
# #                     col.markdown(f"🟠 **{op['operationId'][:4]}**")
# #                     col.caption("En cours")
# #                 elif output2.get("blocked") and output2.get("blocked_at") and op["operationId"] == output2["blocked_at"]["operationId"]:
# #                     col.markdown(f"🔴 **{op['operationId'][:4]}**")
# #                     col.caption("⛔ Bloqué")
# #                 else:
# #                     col.markdown(f"⚪ {op['operationId'][:4]}")
# #                     col.caption("À venir")

# #             # Pièces en attente (info seulement)
# #             if output2.get("waiting_parts"):
# #                 st.markdown("**⏳ Pièces en attente de livraison :**")
# #                 for p in output2["waiting_parts"]:
# #                     if p["days_remaining"] > 0:
# #                         st.markdown(f"- ⏳ {p['itemCode']} × {p['qty_ordered']} ({p['supplier']}, encore {p['days_remaining']}j)")
# #                     else:
# #                         st.markdown(f"- 📦 {p['itemCode']} × {p['qty_ordered']} ({p['supplier']}, ETA atteinte — lancez Sentinelle)")

# #         else:
# #             # Sentinelle classique
# #             ev_col1, ev_col2, ev_col3, ev_col4 = st.columns(4)
# #             risk_icons = {"VERT": "🟢", "ORANGE": "🟠", "ROUGE": "🔴"}
# #             init_risk = output2.get("initial_risk_level", "?")
# #             curr_risk = output2.get("current_risk_level", "?")
# #             evolution = output2.get("risk_evolution", "?")
# #             warning = output2.get("warning_status", "?")

# #             ev_col1.metric("Risque initial", f"{risk_icons.get(init_risk, '⚪')} {init_risk}")
# #             ev_col2.metric("Risque actuel", f"{risk_icons.get(curr_risk, '⚪')} {curr_risk}")
# #             ev_icons = {"BAISSE": "📉", "STABLE": "➡️", "HAUSSE": "📈"}
# #             ev_col3.metric("Évolution", f"{ev_icons.get(evolution, '?')} {evolution}")
# #             w_icons = {"LEVE": "✅", "CONFIRME": "🔴", "EN_SURVEILLANCE": "🔍"}
# #             ev_col4.metric("Warning", f"{w_icons.get(warning, '?')} {warning}")

# #             if warning == "LEVE":
# #                 st.success(f"✅ **Risque levé** — {output2['sentinelle_message']}")
# #             elif warning == "CONFIRME":
# #                 st.error(f"🔴 **Risque confirmé** — {output2['sentinelle_message']}")
# #             else:
# #                 st.warning(f"🔍 **En surveillance** — {output2['sentinelle_message']}")

# #             # ── Suivi pièces ──
# #             tracking = output2.get("parts_tracking", [])
# #             if tracking:
# #                 st.markdown("---")
# #                 st.markdown("#### 📦 Suivi des pièces")
# #                 track_rows = []
# #                 for pt in tracking:
# #                     status_icons = {"REÇU": "✅", "EN_ATTENTE": "⏳", "MANQUANT": "❌"}
# #                     track_rows.append({
# #                         "Composant": pt["itemCode"],
# #                         "Statut": f"{status_icons.get(pt['current_status'], '?')} {pt['current_status']}",
# #                         "Fournisseur": pt.get("supplier", "—"),
# #                         "ETA initiale": pt.get("eta_initial", "—"),
# #                         "ETA actualisée": pt.get("eta_updated", "—"),
# #                         "Qté reçue": pt.get("qty_received", 0),
# #                     })
# #                 st.dataframe(pd.DataFrame(track_rows), use_container_width=True, hide_index=True)

# #             # ── Impact actualisé ──
# #             st.markdown("---")
# #             st.markdown("#### 📅 Impact actualisé")

# #             imp_col1, imp_col2, imp_col3 = st.columns(3)
# #             imp_col1.metric("Date de fin", output2.get("updated_eta_end", "—"))
# #             imp_col1.caption("Calcul : date lancement + durée prod + retard pièces.")
# #             imp_col2.metric("Retard actualisé", f"+{output2.get('updated_delay_days', 0)} j")
# #             imp_col2.caption("Calcul : fin estimée – due date client.")
# #             imp_col3.metric("Priorité reprise", f"{output2.get('resume_priority', '?')}/5")
# #             imp_col3.caption("1=immédiat, 5=non prioritaire.")

# #         # ── Comparaison avec/sans IA ──
# #         st.markdown("---")
# #         st.markdown("#### 🔀 Comparaison : avec vs sans recommandation IA")

# #         maestro_delay = m_ref.get("estimated_delay_days", 0)
# #         if source_type == "simulation":
# #             # advance_time ne constate pas l'arrivée des pièces → le retard reste celui de Maestro
# #             actual_delay = maestro_delay
# #         else:
# #             actual_delay = output2.get("updated_delay_days", 0)

# #         comp_data = {
# #             "Scénario": [
# #                 "Suivi recommandation Maestro",
# #                 "Plan initial sans IA",
# #             ],
# #             "Retard estimé": [
# #                 f"+{actual_delay} j" if actual_delay > 0 else "Aucun",
# #                 f"+{maestro_delay} j" if maestro_delay > 0 else "Non quantifié",
# #             ],
# #         }
# #         st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)

# #         # ── Plan B ──
# #         if source_type == "sentinelle" and output2.get("plan_b_needed"):
# #             st.markdown("---")
# #             st.markdown("#### 🚨 Plan B — Reprogrammation (worst case)")
# #             prop = output2.get("rescheduling_proposal")
# #             if prop:
# #                 st.error(
# #                     f"🔄 **{prop['label']}**\n"
# #                     f"- Lancement : {prop['launch_date']}\n"
# #                     f"- Fin estimée : {prop['estimated_completion']}\n"
# #                     f"- Retard : +{prop['delay_client_days']}j — Pénalités : {prop['penalty_eur']:,.0f} €"
# #                 )
# #         elif source_type == "simulation" and output2.get("blocked"):
# #             st.markdown("---")
# #             st.markdown("#### 🚨 Blocage détecté — Replanification nécessaire")
# #             resch = m_ref.get("rescheduling_options", [])
# #             if resch:
# #                 for opt in resch:
# #                     st.warning(
# #                         f"🔄 **{opt['label']}** — retard +{opt['delay_client_days']}j, "
# #                         f"pénalités {opt['penalty_eur']:,.0f}€"
# #                     )
# #         else:
# #             st.success("✅ Pas de Plan B nécessaire — situation sous contrôle.")

# #         # ── Prompts et JSON ──
# #         if source_type == "sentinelle":
# #             _s_prompt = build_live_context_sentinelle(
# #                 selected_of2, order2.get("priority", "?"), order2.get("dueDate", "?")[:10],
# #                 m_ref, order2["stock"],
# #                 output2.get("still_missing_components", []), output2.get("resolved_components", []),
# #             )
# #             with st.expander("📝 Prompt envoyé à Sentinelle"):
# #                 st.code(SENTINELLE_SYSTEM_PROMPT, language="markdown")
# #                 st.code(_s_prompt, language="markdown")

# #         with st.expander("🔧 JSON technique"):
# #             st.json(output2)

# """
# Page 2 — Maestro & Sentinelle (Décisions et impacts)

# Cette page aide à comprendre les décisions prises par les agents :
# - lecture du film de production,
# - comparaison entre avancement production et arrivée des pièces,
# - statut des actions fournisseurs,
# - options de replanification,
# - impact estimé avec ou sans appui IA.
# """

# import streamlit as st
# import pandas as pd
# import sys, os
# from datetime import datetime, timezone, date


# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from data import (
#     build_seed_orders, ROUTING, WORK_HOURS_PER_DAY, SUPPLIERS_DATA,
#     _check_availability, _find_cutoff, _find_last_doable,
#     build_live_context_maestro, build_live_context_sentinelle,
#     MAESTRO_SYSTEM_PROMPT, SENTINELLE_SYSTEM_PROMPT,
# )


# st.set_page_config(page_title="Maestro & Sentinelle", page_icon="🧠", layout="wide")


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


# def days_remaining_color(days_left):
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
#     f"<span style='font-size:1.3em; color:white;'>📅 Date du jour : <b>{TODAY.strftime('%d/%m/%Y')}</b></span>"
#     f"</div>",
#     unsafe_allow_html=True,
# )


# st.title("🧠 Maestro & Sentinelle — Décisions et impacts")
# st.caption(
#     "Cette page permet de comprendre **pourquoi l’IA recommande un lancement, un décalage ou une replanification**, "
#     "et comment le risque évolue dans le temps au regard du stock, des pièces attendues et des étapes de production."
# )


# st.divider()


# # =============================================================================
# # Onglets
# # =============================================================================


# tab1, tab2 = st.tabs([
#     "🎼 Maestro — Stratégie de lancement",
#     "🔭 Sentinelle — Surveillance et actualisation",
# ])


# # =============================================================================
# # Onglet Maestro
# # =============================================================================


# with tab1:
#     st.markdown("### 🎼 Maestro : Lecture du film de production et décision de lancement")
#     st.caption(
#         "Maestro croise la gamme, les temps de traversée, la disponibilité matière, "
#         "les ETA fournisseurs et les contraintes client. "
#         "Sa question centrale est simple : *la pièce sera-t-elle là avant l’étape où elle devient indispensable ?*"
#     )

#     m_outputs = st.session_state["maestro_outputs"]

#     if not m_outputs:
#         st.info("Aucune analyse Maestro disponible. Lancez d’abord Maestro depuis le Cockpit.")
#     else:
#         m_keys = [k for k in m_outputs if k in orders]
#         selected_of = st.selectbox(
#             "Sélectionner un OF :",
#             options=m_keys,
#             format_func=lambda x: f"{orders[x]['orderNumber']} — {orders[x]['scenario_label']}",
#             key="m_select",
#         )

#         output = m_outputs[selected_of]
#         order = orders[selected_of]

#         # ── Jours restants ──
#         due_dt = datetime.fromisoformat(order["dueDate"].replace("Z", "+00:00"))
#         days_left = (due_dt - NOW_UTC).days
#         dl_icon, dl_color = days_remaining_color(days_left)

#         col_dl, col_risk, col_action = st.columns(3)
#         with col_dl:
#             st.markdown(
#                 f"<div style='text-align:center; padding:12px; border:3px solid {dl_color}; "
#                 f"border-radius:10px;'>"
#                 f"<div style='font-size:2.2em; font-weight:bold; color:{dl_color};'>"
#                 f"{dl_icon} {days_left} j</div>"
#                 f"<div>avant l’échéance client</div></div>",
#                 unsafe_allow_html=True,
#             )
#         with col_risk:
#             risk = output["risk_level"]
#             score = output["global_risk_score"]
#             risk_icons = {"VERT": "🟢", "ORANGE": "🟠", "ROUGE": "🔴"}
#             st.metric(f"{risk_icons.get(risk, '⚪')} Risque estimé", f"{risk} ({score}/100)")
#         with col_action:
#             action = output.get("operator_decision") or output.get("recommended_action", "?")
#             action_labels = {
#                 "LANCER_IMMEDIAT": "✅ Lancer immédiatement",
#                 "LANCER_DECALE": "⚠️ Décaler le lancement",
#                 "REPORTER_ET_REPLANIFIER": "🛑 Reporter",
#             }
#             st.metric("Décision retenue", action_labels.get(action, action))

#         if output.get("operator_decision"):
#             st.success(f"**Consigne atelier** : {output.get('instruction', '—')}")
#         else:
#             st.warning("⏳ Décision opérateur non encore validée.")

#         # ── Impact planning ──
#         st.markdown("---")
#         st.markdown("#### ⏱️ Impact estimé sur le planning")

#         ic1, ic2, ic3, ic4 = st.columns(4)
#         ic1.metric("Probabilité de blocage", f"{output['probabilite_blocage_pct']}%")
#         ic1.caption("Estimation : probabilité que l’OF atteigne l’étape critique avant l’arrivée des pièces.")
#         ic2.metric("Retard estimé", f"{output['estimated_delay_days']} j")
#         ic2.caption("Estimation : écart entre avancement production et disponibilité matière.")
#         ic3.metric("Pénalités estimées", f"{output['estimated_penalty_eur']:,.0f} €")
#         ic3.caption("Estimation : retard prévisionnel multiplié par la pénalité journalière SLA.")
#         ic4.metric("Durée de production", f"{output.get('estimated_production_days', '?')} j")
#         ic4.caption("Estimation : somme des durées d’étapes ramenée en jours ouvrés.")

#         if output.get("sla_impact"):
#             st.caption(f"📋 **Impact SLA** : {output['sla_impact']}")

#         # ──────────────────────────────────────────────────────
#         # FILM DE PRODUCTION EXPLICITE
#         # ──────────────────────────────────────────────────────
#         st.markdown("---")
#         st.markdown("#### 🎬 Film de production — Lecture pas à pas")
#         st.caption(
#             "Chaque étape indique sa durée propre, le temps cumulé depuis le démarrage de l’OF, "
#             "et les éventuels points de vigilance matière."
#         )

#         etape = output.get("etape_a_risque")
#         missing_codes = {mc["itemCode"] for mc in output.get("missing_components", [])}

#         # ETA fournisseur par composant
#         supplier_etas = {}
#         for plan in output.get("supplier_order_plan", []):
#             supplier_etas[plan["itemCode"]] = plan["estimated_lead_days"]

#         # Décalage lancement
#         launch_offset = 0
#         if output.get("recommended_action") == "LANCER_DECALE" and output.get("recommended_launch_date"):
#             try:
#                 ld = datetime.strptime(output["recommended_launch_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
#                 launch_offset = (ld - NOW_UTC).days
#             except (ValueError, TypeError):
#                 launch_offset = 1

#         for op in ROUTING:
#             dur_days = round(op["duration_hours"] / WORK_HOURS_PER_DAY, 1)
#             cumul_days = round(op["cumulative_end_hours"] / WORK_HOURS_PER_DAY, 1)
#             reach_days = round(op["cumulative_start_hours"] / WORK_HOURS_PER_DAY, 1)

#             blocked_items = set(op.get("requiredComponents", [])) & missing_codes
#             is_risk = etape and op["operationId"] == etape["operationId"]

#             icon = "🔴" if is_risk else ("🟠" if blocked_items else "🟢")
#             comps = ", ".join(op.get("requiredComponents", [])) or "—"

#             st.markdown(
#                 f"{icon} **{op['operationId']}** — {op['description']}  \n"
#                 f"&nbsp;&nbsp;&nbsp;&nbsp;⏱️ Durée étape : **{dur_days}j** "
#                 f"| Cumul depuis démarrage : **{cumul_days}j** "
#                 f"| Composants requis : {comps}"
#             )

#             if blocked_items:
#                 for item in blocked_items:
#                     eta = supplier_etas.get(item)
#                     eff_reach = reach_days + launch_offset
#                     if eta is not None:
#                         if eta <= eff_reach:
#                             st.markdown(
#                                 f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
#                                 f"✅ {item} : ETA J+{eta} ≤ étape J+{eff_reach:.0f} → **arrivée compatible avec le flux**"
#                             )
#                         else:
#                             st.markdown(
#                                 f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
#                                 f"🔴 **Risque sur `{item}` à cette étape** — "
#                                 f"ETA J+{eta} > étape J+{eff_reach:.0f}"
#                             )
#                     else:
#                         st.markdown(
#                             f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
#                             f"🟠 {item} manquant — aucun plan fournisseur sécurisé"
#                         )

#         # Texte récapitulatif temporel
#         if etape and output.get("supplier_order_plan"):
#             relevant = [p for p in output["supplier_order_plan"]
#                         if p["itemCode"] == etape.get("composant_manquant")]
#             if relevant:
#                 eta = relevant[0]["estimated_lead_days"]
#                 reach = etape["time_to_reach_days"]
#                 st.markdown("---")

#                 if output.get("recommended_action") == "LANCER_DECALE":
#                     new_reach = reach + launch_offset
#                     st.info(
#                         f"📐 **Lecture temporelle** : si l’OF démarre maintenant, "
#                         f"l’étape {etape['operationId']} sera atteinte dans **{reach} jours**. "
#                         f"ETA pièce : J+{eta} → risque de blocage.\n\n"
#                         f"💡 **Alternative proposée** : décaler le lancement de **{launch_offset} jour(s)**. "
#                         f"L’étape critique serait alors atteinte à J+{new_reach:.0f}, "
#                         f"pour une ETA pièce J+{eta} → risque réduit."
#                     )
#                 elif eta > reach:
#                     st.error(
#                         f"📐 **Lecture temporelle** : si l’OF démarre maintenant, "
#                         f"l’étape {etape['operationId']} sera atteinte dans **{reach} jours**. "
#                         f"ETA pièce : J+{eta} → **blocage probable**."
#                     )
#                 else:
#                     st.success(
#                         f"📐 **Lecture temporelle** : la pièce est attendue en J+{eta}, "
#                         f"et l’étape {etape['operationId']} sera atteinte en J+{reach} → **flux sécurisé**."
#                     )

#         # ── Production vs Arrivée chart ──
#         st.markdown("---")
#         st.markdown("#### 📈 Avancement production vs arrivée pièce")

#         if etape and output.get("supplier_order_plan"):
#             relevant_plan = [p for p in output["supplier_order_plan"]
#                              if p["itemCode"] == etape["composant_manquant"]]
#             sup_eta_days = relevant_plan[0]["estimated_lead_days"] if relevant_plan else None

#             steps_data = []
#             for op in ROUTING:
#                 day = round(op["cumulative_start_hours"] / WORK_HOURS_PER_DAY, 1)
#                 steps_data.append({
#                     "Étape": op["operationId"],
#                     "Production (jour)": day,
#                 })

#             col_chart, col_legend = st.columns([3, 1])
#             with col_chart:
#                 chart_df = pd.DataFrame(steps_data)
#                 chart_df["Production"] = chart_df["Production (jour)"]
#                 if sup_eta_days:
#                     chart_df["ETA pièce"] = sup_eta_days
#                     st.line_chart(chart_df.set_index("Étape")[["Production", "ETA pièce"]])
#                 else:
#                     st.line_chart(chart_df.set_index("Étape")[["Production"]])

#             with col_legend:
#                 st.markdown("**Lecture du graphique**")
#                 st.markdown("📈 Courbe production : progression dans la gamme")
#                 if sup_eta_days:
#                     st.markdown(f"📦 ETA {etape['composant_manquant']} : J+{sup_eta_days}")
#                 st.markdown("⚠️ Zone de croisement = zone de risque potentiel")
#         elif not etape:
#             st.success("✅ Aucune étape critique identifiée — pas de tension matière bloquante.")

#         # ── Créneaux reprogrammation ──
#         opts = output.get("rescheduling_options", [])
#         if opts:
#             st.markdown("---")
#             st.markdown("#### 🔄 Créneaux de reprogrammation")
#             st.caption("Maestro propose plusieurs options avec leur impact sur le délai client et le coût du retard.")

#             for i, opt in enumerate(opts):
#                 with st.expander(f"**Option {i+1}** : {opt['label']}", expanded=(i == 0)):
#                     st.markdown(f"- Date de lancement : **{opt['launch_date']}**")
#                     st.markdown(f"- Fin estimée OF : {opt['estimated_completion']}")
#                     st.markdown(f"- Retard client estimé : **+{opt['delay_client_days']}j**")
#                     st.markdown(f"- Pénalités estimées : {opt['penalty_eur']:,.0f} €")
#                     st.markdown(f"- *{opt['comment']}*")
#                     if opt.get("delay_client_days", 0) > 0:
#                         st.warning("⚠️ Cette option peut créer de la tension sur d’autres OF si la charge atelier est déjà élevée.")

#             chosen = output.get("chosen_rescheduling")
#             if chosen:
#                 st.success(f"✅ Décision enregistrée : **{chosen['label']}** — retard estimé +{chosen['delay_client_days']}j")

#         # ── Emails fournisseur (avec statut validation) ──
#         emails = output.get("simulated_emails", [])
#         if emails:
#             st.markdown("---")
#             st.markdown("#### 📧 Actions fournisseur préparées")
#             st.caption("Maestro prépare les messages nécessaires pour sécuriser les composants critiques.")

#             for email in emails:
#                 status_label = email.get("action_label", "⏳ En attente de validation")
#                 st.markdown(f"**{email['to_name']}** — {email['subject']} → {status_label}")
#                 with st.expander("📨 Voir le message"):
#                     st.markdown(f"**À** : {email['to_name']} <{email['to']}>")
#                     st.markdown(f"**Objet** : {email['subject']}")
#                     st.divider()
#                     st.text(email["body"])

#         # ── Stock & facteurs ──
#         st.markdown("---")
#         st.markdown("#### 📋 Pourquoi cette recommandation ?")

#         st.markdown("**Lecture stock / besoin / étape**")
#         stock_rows = []
#         for comp in order["components"]:
#             needed = comp["qtyPerUnit"] * order["quantity"]
#             avail = order["stock"].get(comp["itemCode"], 0)
#             step = "—"
#             for op in ROUTING:
#                 if comp["itemCode"] in op.get("requiredComponents", []):
#                     step = op["operationId"]
#                     break
#             stock_rows.append({
#                 "Composant": comp["itemCode"],
#                 "Besoin": needed,
#                 "Dispo": avail,
#                 "Étape de consommation": step,
#                 "État": "✅" if avail >= needed else "❌",
#                 "Critique": "🔴" if comp.get("isCritical") else "",
#             })
#         st.dataframe(pd.DataFrame(stock_rows), use_container_width=True, hide_index=True)

#         if output.get("risk_factors"):
#             st.markdown("**Facteurs de risque pris en compte**")
#             st.dataframe(pd.DataFrame(output["risk_factors"]), use_container_width=True, hide_index=True)

#         if output.get("reasoning"):
#             with st.expander("💬 Explication détaillée de l’analyse Maestro"):
#                 st.write(output["reasoning"])

#         # ── Prompts et JSON ──
#         _missing = _check_availability(order["components"], order["quantity"], order["stock"])
#         _cutoff = _find_cutoff(ROUTING, _missing)
#         _last = _find_last_doable(ROUTING, _cutoff)
#         _prompt = build_live_context_maestro(order, order["stock"], _missing, _cutoff, _last)

#         with st.expander("📝 Prompt envoyé à Maestro"):
#             st.code(MAESTRO_SYSTEM_PROMPT, language="markdown")
#             st.code(_prompt, language="markdown")
#         with st.expander("🔧 JSON technique"):
#             st.json(output)



# # =============================================================================
# # Onglet Sentinelle
# # =============================================================================


# with tab2:
#     st.markdown("### 🔭 Sentinelle : Suivi des pièces et évolution du risque")
#     st.caption(
#         "Sentinelle vérifie dans le temps si les hypothèses de Maestro se confirment. "
#         "Elle suit les livraisons, réévalue le niveau de risque et lève l’alerte dès que le flux est sécurisé."
#     )

#     s_outputs = st.session_state["sentinelle_outputs"]
#     time_sim = st.session_state["time_sim_results"]

#     # Sentinelle = source de vérité pour le risque
#     # time_sim = info de progression production uniquement
#     all_outputs = {}
#     for k, v in s_outputs.items():
#         all_outputs[k] = ("sentinelle", v)
#     for k, v in time_sim.items():
#         if k not in all_outputs:
#             all_outputs[k] = ("simulation", v)

#     if not all_outputs:
#         st.info("Aucune analyse Sentinelle ni simulation temporelle disponible.")
#     else:
#         s_keys = [k for k in all_outputs if k in orders]
#         selected_of2 = st.selectbox(
#             "Sélectionner un OF :",
#             options=s_keys,
#             format_func=lambda x: f"{orders[x]['orderNumber']} — {orders[x]['scenario_label']}",
#             key="s_select",
#         )

#         source_type, output2 = all_outputs[selected_of2]
#         order2 = orders[selected_of2]
#         m_ref = st.session_state["maestro_outputs"].get(selected_of2, {})

#         # ── Jours restants ──
#         due_dt2 = datetime.fromisoformat(order2["dueDate"].replace("Z", "+00:00"))
#         days_left2 = (due_dt2 - NOW_UTC).days
#         dl_icon2, dl_color2 = days_remaining_color(days_left2)

#         st.markdown(
#             f"<div style='text-align:center; padding:8px; border:2px solid {dl_color2}; "
#             f"border-radius:8px; margin-bottom:12px;'>"
#             f"<span style='font-size:1.5em; font-weight:bold; color:{dl_color2};'>"
#             f"{dl_icon2} {days_left2} jours restants</span>"
#             f"<span> avant l’échéance client</span></div>",
#             unsafe_allow_html=True,
#         )

#         # ── Évolution du risque ──
#         st.markdown("---")
#         st.markdown("#### 📊 Évolution du risque dans le temps")

#         if source_type == "simulation":
#             # Simulation temporelle (avancement seul, pas de constat pièces)
#             ev_col1, ev_col2, ev_col3 = st.columns(3)
#             risk_icons = {"VERT": "🟢", "ORANGE": "🟠", "ROUGE": "🔴"}
#             init_risk = m_ref.get("risk_level", "?")

#             ev_col1.metric("Risque initial Maestro", f"{risk_icons.get(init_risk, '⚪')} {init_risk}")
#             ev_col2.metric("Jour simulé", f"J+{output2.get('days_advanced', 0)}")
#             if output2.get("days_remaining_to_risk") is not None:
#                 ev_col3.metric("Distance au point critique", f"{output2['days_remaining_to_risk']}j")
#             else:
#                 ev_col3.metric("Distance au point critique", "—")

#             if output2.get("blocked"):
#                 st.error(f"🔴 {output2['message']}")
#             elif output2.get("missing_components"):
#                 st.warning(f"🟠 {output2['message']}")
#             else:
#                 st.success(f"🟢 {output2['message']}")

#             st.info("💡 À ce stade, la production avance mais l’arrivée des pièces n’est pas encore confirmée. Lancez Sentinelle pour contrôle.")

#             # Timeline de progression
#             st.markdown("---")
#             st.markdown("#### 🎬 Progression simulée du film de production")
#             hours = output2.get("hours_elapsed", 0)
#             sim_cols = st.columns(len(ROUTING))
#             for i, (col, op) in enumerate(zip(sim_cols, ROUTING)):
#                 if hours >= op["cumulative_end_hours"]:
#                     col.markdown(f"✅ **{op['operationId'][:4]}**")
#                     col.caption("Terminé")
#                 elif hours >= op["cumulative_start_hours"]:
#                     col.markdown(f"🟠 **{op['operationId'][:4]}**")
#                     col.caption("En cours")
#                 elif output2.get("blocked") and output2.get("blocked_at") and op["operationId"] == output2["blocked_at"]["operationId"]:
#                     col.markdown(f"🔴 **{op['operationId'][:4]}**")
#                     col.caption("Blocage atteint")
#                 else:
#                     col.markdown(f"⚪ {op['operationId'][:4]}")
#                     col.caption("À venir")

#             # Pièces en attente (info seulement)
#             if output2.get("waiting_parts"):
#                 st.markdown("**⏳ Composants en attente de livraison**")
#                 for p in output2["waiting_parts"]:
#                     if p["days_remaining"] > 0:
#                         st.markdown(f"- ⏳ {p['itemCode']} × {p['qty_ordered']} ({p['supplier']}, encore {p['days_remaining']}j)")
#                     else:
#                         st.markdown(f"- 📦 {p['itemCode']} × {p['qty_ordered']} ({p['supplier']}, ETA atteinte — lancez Sentinelle)")

#         else:
#             # Sentinelle classique
#             ev_col1, ev_col2, ev_col3, ev_col4 = st.columns(4)
#             risk_icons = {"VERT": "🟢", "ORANGE": "🟠", "ROUGE": "🔴"}
#             init_risk = output2.get("initial_risk_level", "?")
#             curr_risk = output2.get("current_risk_level", "?")
#             evolution = output2.get("risk_evolution", "?")
#             warning = output2.get("warning_status", "?")

#             ev_col1.metric("Risque initial", f"{risk_icons.get(init_risk, '⚪')} {init_risk}")
#             ev_col2.metric("Risque actuel", f"{risk_icons.get(curr_risk, '⚪')} {curr_risk}")
#             ev_icons = {"BAISSE": "📉", "STABLE": "➡️", "HAUSSE": "📈"}
#             ev_col3.metric("Tendance", f"{ev_icons.get(evolution, '?')} {evolution}")
#             w_icons = {"LEVE": "✅", "CONFIRME": "🔴", "EN_SURVEILLANCE": "🔍"}
#             ev_col4.metric("Alerte", f"{w_icons.get(warning, '?')} {warning}")

#             if warning == "LEVE":
#                 st.success(f"✅ **Risque levé** — {output2['sentinelle_message']}")
#             elif warning == "CONFIRME":
#                 st.error(f"🔴 **Risque confirmé** — {output2['sentinelle_message']}")
#             else:
#                 st.warning(f"🔍 **Risque sous surveillance** — {output2['sentinelle_message']}")

#             # ── Suivi pièces ──
#             tracking = output2.get("parts_tracking", [])
#             if tracking:
#                 st.markdown("---")
#                 st.markdown("#### 📦 Suivi détaillé des composants")
#                 track_rows = []
#                 for pt in tracking:
#                     status_icons = {"REÇU": "✅", "EN_ATTENTE": "⏳", "MANQUANT": "❌"}
#                     track_rows.append({
#                         "Composant": pt["itemCode"],
#                         "Statut": f"{status_icons.get(pt['current_status'], '?')} {pt['current_status']}",
#                         "Fournisseur": pt.get("supplier", "—"),
#                         "ETA initiale": pt.get("eta_initial", "—"),
#                         "ETA actualisée": pt.get("eta_updated", "—"),
#                         "Qté reçue": pt.get("qty_received", 0),
#                     })
#                 st.dataframe(pd.DataFrame(track_rows), use_container_width=True, hide_index=True)

#             # ── Impact actualisé ──
#             st.markdown("---")
#             st.markdown("#### 📅 Impact actualisé sur l’OF")

#             imp_col1, imp_col2, imp_col3 = st.columns(3)
#             imp_col1.metric("Date de fin estimée", output2.get("updated_eta_end", "—"))
#             imp_col1.caption("Estimation : date de lancement + durée production + impact retard fournisseur.")
#             imp_col2.metric("Retard actualisé", f"+{output2.get('updated_delay_days', 0)} j")
#             imp_col2.caption("Estimation : date de fin révisée moins due date client.")
#             imp_col3.metric("Priorité métier", f"{output2.get('resume_priority', '?')}/5")
#             imp_col3.caption("Plus la note est faible, plus l’OF doit être traité rapidement.")

#         # ── Comparaison avec/sans IA ──
#         st.markdown("---")
#         st.markdown("#### 🔀 Comparaison : avec pilotage IA vs sans pilotage IA")

#         maestro_delay = m_ref.get("estimated_delay_days", 0)
#         if source_type == "simulation":
#             actual_delay = maestro_delay
#         else:
#             actual_delay = output2.get("updated_delay_days", 0)

#         comp_data = {
#             "Scénario": [
#                 "Pilotage avec recommandations IA",
#                 "Plan initial sans ajustement IA",
#             ],
#             "Retard estimé": [
#                 f"+{actual_delay} j" if actual_delay > 0 else "Aucun",
#                 f"+{maestro_delay} j" if maestro_delay > 0 else "Non quantifié",
#             ],
#         }
#         st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)

#         # ── Plan B ──
#         if source_type == "sentinelle" and output2.get("plan_b_needed"):
#             st.markdown("---")
#             st.markdown("#### 🚨 Plan B — Reprogrammation nécessaire")
#             prop = output2.get("rescheduling_proposal")
#             if prop:
#                 st.error(
#                     f"🔄 **{prop['label']}**\n"
#                     f"- Lancement : {prop['launch_date']}\n"
#                     f"- Fin estimée : {prop['estimated_completion']}\n"
#                     f"- Retard : +{prop['delay_client_days']}j — Pénalités : {prop['penalty_eur']:,.0f} €"
#                 )
#         elif source_type == "simulation" and output2.get("blocked"):
#             st.markdown("---")
#             st.markdown("#### 🚨 Blocage atteint — Replanification à instruire")
#             resch = m_ref.get("rescheduling_options", [])
#             if resch:
#                 for opt in resch:
#                     st.warning(
#                         f"🔄 **{opt['label']}** — retard +{opt['delay_client_days']}j, "
#                         f"pénalités {opt['penalty_eur']:,.0f}€"
#                     )
#         else:
#             st.success("✅ Pas de plan B nécessaire à ce stade — situation maîtrisée.")

#         # ── Prompts et JSON ──
#         if source_type == "sentinelle":
#             _s_prompt = build_live_context_sentinelle(
#                 selected_of2, order2.get("priority", "?"), order2.get("dueDate", "?")[:10],
#                 m_ref, order2["stock"],
#                 output2.get("still_missing_components", []), output2.get("resolved_components", []),
#             )
#             with st.expander("📝 Prompt envoyé à Sentinelle"):
#                 st.code(SENTINELLE_SYSTEM_PROMPT, language="markdown")
#                 st.code(_s_prompt, language="markdown")

#         with st.expander("🔧 JSON technique"):
#             st.json(output2)
"""
Page 2 — Maestro & Sentinelle (Decisions and impacts)


This page helps explain the decisions made by the agents:
- reading the production flow,
- comparing production progress with part arrivals,
- supplier action status,
- rescheduling options,
- estimated impact with or without AI support.
"""


import streamlit as st
import pandas as pd
import sys, os
from datetime import datetime, timezone, date



sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data import (
    build_seed_orders, ROUTING, WORK_HOURS_PER_DAY, SUPPLIERS_DATA,
    _check_availability, _find_cutoff, _find_last_doable,
    build_live_context_maestro, build_live_context_sentinelle,
    MAESTRO_SYSTEM_PROMPT, SENTINELLE_SYSTEM_PROMPT,
)



st.set_page_config(page_title="Maestro & Sentinelle", page_icon="🧠", layout="wide")



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



def days_remaining_color(days_left):
    if days_left >= 15:
        return "🟢", "#2ecc71"
    elif days_left >= 8:
        return "🟠", "#f39c12"
    else:
        return "🔴", "#e74c3c"




# =============================================================================
# Header
# =============================================================================



st.markdown(
    f"<div style='text-align:center; padding:10px; background:linear-gradient(90deg,#1a1a2e,#16213e); "
    f"border-radius:10px; margin-bottom:12px;'>"
    f"<span style='font-size:1.3em; color:white;'>📅 Current date: <b>{TODAY.strftime('%d/%m/%Y')}</b></span>"
    f"</div>",
    unsafe_allow_html=True,
)



st.title("🧠 Maestro & Sentinelle — Decisions and impacts")
st.caption(
    "This page helps explain **why the AI recommends launching, delaying, or rescheduling**, "
    "and how the risk evolves over time based on stock, expected parts, and production steps."
)



st.divider()



# =============================================================================
# Tabs
# =============================================================================



tab1, tab2 = st.tabs([
    "🎼 Maestro — Launch strategy",
    "🔭 Sentinelle — Monitoring and updates",
])



# =============================================================================
# Maestro tab
# =============================================================================



with tab1:
    st.markdown("### 🎼 Maestro: Reading the production flow and launch decision")
    st.caption(
        "Maestro cross-checks routing, throughput times, material availability, "
        "supplier ETAs, and customer constraints. "
        "Its core question is simple: *will the part be there before the step where it becomes essential?*"
    )


    m_outputs = st.session_state["maestro_outputs"]


    if not m_outputs:
        st.info("No Maestro analysis available. Run Maestro first from the Cockpit.")
    else:
        m_keys = [k for k in m_outputs if k in orders]
        selected_of = st.selectbox(
            "Select a production order:",
            options=m_keys,
            format_func=lambda x: f"{orders[x]['orderNumber']} — {orders[x]['scenario_label']}",
            key="m_select",
        )


        output = m_outputs[selected_of]
        order = orders[selected_of]


        # ── Remaining days ──
        due_dt = datetime.fromisoformat(order["dueDate"].replace("Z", "+00:00"))
        days_left = (due_dt - NOW_UTC).days
        dl_icon, dl_color = days_remaining_color(days_left)


        col_dl, col_risk, col_action = st.columns(3)
        with col_dl:
            st.markdown(
                f"<div style='text-align:center; padding:12px; border:3px solid {dl_color}; "
                f"border-radius:10px;'>"
                f"<div style='font-size:2.2em; font-weight:bold; color:{dl_color};'>"
                f"{dl_icon} {days_left} d</div>"
                f"<div>before the customer due date</div></div>",
                unsafe_allow_html=True,
            )
        with col_risk:
            risk = output["risk_level"]
            score = output["global_risk_score"]
            risk_icons = {"VERT": "🟢", "ORANGE": "🟠", "ROUGE": "🔴"}
            st.metric(f"{risk_icons.get(risk, '⚪')} Estimated risk", f"{risk} ({score}/100)")
        with col_action:
            action = output.get("operator_decision") or output.get("recommended_action", "?")
            action_labels = {
                "LANCER_IMMEDIAT": "✅ Launch immediately",
                "LANCER_DECALE": "⚠️ Delay launch",
                "REPORTER_ET_REPLANIFIER": "🛑 Postpone",
            }
            st.metric("Selected decision", action_labels.get(action, action))


        if output.get("operator_decision"):
            st.success(f"**Workshop instruction** : {output.get('instruction', '—')}")
        else:
            st.warning("⏳ Operator decision not yet validated.")


        # ── Planning impact ──
        st.markdown("---")
        st.markdown("#### ⏱️ Estimated impact on the schedule")


        ic1, ic2, ic3, ic4 = st.columns(4)
        ic1.metric("Blocking probability", f"{output['probabilite_blocage_pct']}%")
        ic1.caption("Estimate: probability that the production order reaches the critical step before part arrival.")
        ic2.metric("Estimated delay", f"{output['estimated_delay_days']} d")
        ic2.caption("Estimate: gap between production progress and material availability.")
        ic3.metric("Estimated penalties", f"{output['estimated_penalty_eur']:,.0f} €")
        ic3.caption("Estimate: forecast delay multiplied by the daily SLA penalty.")
        ic4.metric("Production duration", f"{output.get('estimated_production_days', '?')} d")
        ic4.caption("Estimate: sum of step durations converted into working days.")


        if output.get("sla_impact"):
            st.caption(f"📋 **SLA impact** : {output['sla_impact']}")


        # ──────────────────────────────────────────────────────
        # EXPLICIT PRODUCTION FLOW
        # ──────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("#### 🎬 Production flow — Step-by-step reading")
        st.caption(
            "Each step shows its own duration, the cumulative time since the production order started, "
            "and any potential material attention points."
        )


        etape = output.get("etape_a_risque")
        missing_codes = {mc["itemCode"] for mc in output.get("missing_components", [])}


        # Supplier ETA by component
        supplier_etas = {}
        for plan in output.get("supplier_order_plan", []):
            supplier_etas[plan["itemCode"]] = plan["estimated_lead_days"]


        # Launch offset
        launch_offset = 0
        if output.get("recommended_action") == "LANCER_DECALE" and output.get("recommended_launch_date"):
            try:
                ld = datetime.strptime(output["recommended_launch_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                launch_offset = (ld - NOW_UTC).days
            except (ValueError, TypeError):
                launch_offset = 1


        for op in ROUTING:
            dur_days = round(op["duration_hours"] / WORK_HOURS_PER_DAY, 1)
            cumul_days = round(op["cumulative_end_hours"] / WORK_HOURS_PER_DAY, 1)
            reach_days = round(op["cumulative_start_hours"] / WORK_HOURS_PER_DAY, 1)


            blocked_items = set(op.get("requiredComponents", [])) & missing_codes
            is_risk = etape and op["operationId"] == etape["operationId"]


            icon = "🔴" if is_risk else ("🟠" if blocked_items else "🟢")
            comps = ", ".join(op.get("requiredComponents", [])) or "—"


            st.markdown(
                f"{icon} **{op['operationId']}** — {op['description']}  \n"
                f"&nbsp;&nbsp;&nbsp;&nbsp;⏱️ Step duration: **{dur_days}d** "
                f"| Cumulative from start: **{cumul_days}d** "
                f"| Required components: {comps}"
            )


            if blocked_items:
                for item in blocked_items:
                    eta = supplier_etas.get(item)
                    eff_reach = reach_days + launch_offset
                    if eta is not None:
                        if eta <= eff_reach:
                            st.markdown(
                                f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
                                f"✅ {item} : ETA D+{eta} ≤ step D+{eff_reach:.0f} → **arrival compatible with the flow**"
                            )
                        else:
                            st.markdown(
                                f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
                                f"🔴 **Risk on `{item}` at this step** — "
                                f"ETA D+{eta} > step D+{eff_reach:.0f}"
                            )
                    else:
                        st.markdown(
                            f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
                            f"🟠 {item} missing — no secured supplier plan"
                        )


        # Time summary text
        if etape and output.get("supplier_order_plan"):
            relevant = [p for p in output["supplier_order_plan"]
                        if p["itemCode"] == etape.get("composant_manquant")]
            if relevant:
                eta = relevant[0]["estimated_lead_days"]
                reach = etape["time_to_reach_days"]
                st.markdown("---")


                if output.get("recommended_action") == "LANCER_DECALE":
                    new_reach = reach + launch_offset
                    st.info(
                        f"📐 **Timeline reading** : if the production order starts now, "
                        f"step {etape['operationId']} will be reached in **{reach} days**. "
                        f"Part ETA: D+{eta} → risk of blockage.\n\n"
                        f"💡 **Proposed alternative** : delay the launch by **{launch_offset} day(s)**. "
                        f"The critical step would then be reached at D+{new_reach:.0f}, "
                        f"for a part ETA at D+{eta} → reduced risk."
                    )
                elif eta > reach:
                    st.error(
                        f"📐 **Timeline reading** : if the production order starts now, "
                        f"step {etape['operationId']} will be reached in **{reach} days**. "
                        f"Part ETA: D+{eta} → **probable blockage**."
                    )
                else:
                    st.success(
                        f"📐 **Timeline reading** : the part is expected at D+{eta}, "
                        f"and step {etape['operationId']} will be reached at D+{reach} → **flow secured**."
                    )


        # ── Production vs Arrival chart ──
        st.markdown("---")
        st.markdown("#### 📈 Production progress vs part arrival")


        if etape and output.get("supplier_order_plan"):
            relevant_plan = [p for p in output["supplier_order_plan"]
                             if p["itemCode"] == etape["composant_manquant"]]
            sup_eta_days = relevant_plan[0]["estimated_lead_days"] if relevant_plan else None


            steps_data = []
            for op in ROUTING:
                day = round(op["cumulative_start_hours"] / WORK_HOURS_PER_DAY, 1)
                steps_data.append({
                    "Step": op["operationId"],
                    "Production (day)": day,
                })


            col_chart, col_legend = st.columns([3, 1])
            with col_chart:
                chart_df = pd.DataFrame(steps_data)
                chart_df["Production"] = chart_df["Production (day)"]
                if sup_eta_days:
                    chart_df["Part ETA"] = sup_eta_days
                    st.line_chart(chart_df.set_index("Step")[["Production", "Part ETA"]])
                else:
                    st.line_chart(chart_df.set_index("Step")[["Production"]])


            with col_legend:
                st.markdown("**How to read the chart**")
                st.markdown("📈 Production curve: progress through the routing")
                if sup_eta_days:
                    st.markdown(f"📦 ETA {etape['composant_manquant']} : D+{sup_eta_days}")
                st.markdown("⚠️ Crossing zone = potential risk area")
        elif not etape:
            st.success("✅ No critical step identified — no blocking material tension.")


        # ── Rescheduling slots ──
        opts = output.get("rescheduling_options", [])
        if opts:
            st.markdown("---")
            st.markdown("#### 🔄 Rescheduling slots")
            st.caption("Maestro proposes several options with their impact on customer delay and delay cost.")


            for i, opt in enumerate(opts):
                with st.expander(f"**Option {i+1}** : {opt['label']}", expanded=(i == 0)):
                    st.markdown(f"- Launch date : **{opt['launch_date']}**")
                    st.markdown(f"- Estimated production order completion : {opt['estimated_completion']}")
                    st.markdown(f"- Estimated customer delay : **+{opt['delay_client_days']}d**")
                    st.markdown(f"- Estimated penalties : {opt['penalty_eur']:,.0f} €")
                    st.markdown(f"- *{opt['comment']}*")
                    if opt.get("delay_client_days", 0) > 0:
                        st.warning("⚠️ This option may create tension on other production orders if workshop load is already high.")


            chosen = output.get("chosen_rescheduling")
            if chosen:
                st.success(f"✅ Decision recorded : **{chosen['label']}** — estimated delay +{chosen['delay_client_days']}d")


        # ── Supplier emails (with validation status) ──
        emails = output.get("simulated_emails", [])
        if emails:
            st.markdown("---")
            st.markdown("#### 📧 Prepared supplier actions")
            st.caption("Maestro prepares the messages needed to secure critical components.")


            for email in emails:
                status_label = email.get("action_label", "⏳ Pending validation")
                st.markdown(f"**{email['to_name']}** — {email['subject']} → {status_label}")
                with st.expander("📨 View message"):
                    st.markdown(f"**To** : {email['to_name']} <{email['to']}>")
                    st.markdown(f"**Subject** : {email['subject']}")
                    st.divider()
                    st.text(email["body"])


        # ── Stock & factors ──
        st.markdown("---")
        st.markdown("#### 📋 Why this recommendation?")


        st.markdown("**Reading stock / requirement / step**")
        stock_rows = []
        for comp in order["components"]:
            needed = comp["qtyPerUnit"] * order["quantity"]
            avail = order["stock"].get(comp["itemCode"], 0)
            step = "—"
            for op in ROUTING:
                if comp["itemCode"] in op.get("requiredComponents", []):
                    step = op["operationId"]
                    break
            stock_rows.append({
                "Component": comp["itemCode"],
                "Required": needed,
                "Available": avail,
                "Consumption step": step,
                "Status": "✅" if avail >= needed else "❌",
                "Critical": "🔴" if comp.get("isCritical") else "",
            })
        st.dataframe(pd.DataFrame(stock_rows), use_container_width=True, hide_index=True)


        if output.get("risk_factors"):
            st.markdown("**Risk factors taken into account**")
            st.dataframe(pd.DataFrame(output["risk_factors"]), use_container_width=True, hide_index=True)


        if output.get("reasoning"):
            with st.expander("💬 Detailed explanation of the Maestro analysis"):
                st.write(output["reasoning"])


        # ── Prompts and JSON ──
        _missing = _check_availability(order["components"], order["quantity"], order["stock"])
        _cutoff = _find_cutoff(ROUTING, _missing)
        _last = _find_last_doable(ROUTING, _cutoff)
        _prompt = build_live_context_maestro(order, order["stock"], _missing, _cutoff, _last)


        with st.expander("📝 Prompt sent to Maestro"):
            st.code(MAESTRO_SYSTEM_PROMPT, language="markdown")
            st.code(_prompt, language="markdown")
        with st.expander("🔧 Technical JSON"):
            st.json(output)




# =============================================================================
# Sentinelle tab
# =============================================================================



with tab2:
    st.markdown("### 🔭 Sentinelle: Part tracking and risk evolution")
    st.caption(
        "Sentinelle checks over time whether Maestro’s assumptions are confirmed. "
        "It tracks deliveries, reassesses the risk level, and clears the alert as soon as the flow is secured."
    )


    s_outputs = st.session_state["sentinelle_outputs"]
    time_sim = st.session_state["time_sim_results"]


    # Sentinelle = source of truth for the risk
    # time_sim = production progress information only
    all_outputs = {}
    for k, v in s_outputs.items():
        all_outputs[k] = ("sentinelle", v)
    for k, v in time_sim.items():
        if k not in all_outputs:
            all_outputs[k] = ("simulation", v)


    if not all_outputs:
        st.info("No Sentinelle analysis or time simulation available.")
    else:
        s_keys = [k for k in all_outputs if k in orders]
        selected_of2 = st.selectbox(
            "Select a production order:",
            options=s_keys,
            format_func=lambda x: f"{orders[x]['orderNumber']} — {orders[x]['scenario_label']}",
            key="s_select",
        )


        source_type, output2 = all_outputs[selected_of2]
        order2 = orders[selected_of2]
        m_ref = st.session_state["maestro_outputs"].get(selected_of2, {})


        # ── Remaining days ──
        due_dt2 = datetime.fromisoformat(order2["dueDate"].replace("Z", "+00:00"))
        days_left2 = (due_dt2 - NOW_UTC).days
        dl_icon2, dl_color2 = days_remaining_color(days_left2)


        st.markdown(
            f"<div style='text-align:center; padding:8px; border:2px solid {dl_color2}; "
            f"border-radius:8px; margin-bottom:12px;'>"
            f"<span style='font-size:1.5em; font-weight:bold; color:{dl_color2};'>"
            f"{dl_icon2} {days_left2} days remaining</span>"
            f"<span> before the customer due date</span></div>",
            unsafe_allow_html=True,
        )


        # ── Risk evolution ──
        st.markdown("---")
        st.markdown("#### 📊 Risk evolution over time")


        if source_type == "simulation":
            # Time simulation (progress only, no part confirmation)
            ev_col1, ev_col2, ev_col3 = st.columns(3)
            risk_icons = {"VERT": "🟢", "ORANGE": "🟠", "ROUGE": "🔴"}
            init_risk = m_ref.get("risk_level", "?")


            ev_col1.metric("Initial Maestro risk", f"{risk_icons.get(init_risk, '⚪')} {init_risk}")
            ev_col2.metric("Simulated day", f"D+{output2.get('days_advanced', 0)}")
            if output2.get("days_remaining_to_risk") is not None:
                ev_col3.metric("Distance to critical point", f"{output2['days_remaining_to_risk']}d")
            else:
                ev_col3.metric("Distance to critical point", "—")


            if output2.get("blocked"):
                st.error(f"🔴 {output2['message']}")
            elif output2.get("missing_components"):
                st.warning(f"🟠 {output2['message']}")
            else:
                st.success(f"🟢 {output2['message']}")


            st.info("💡 At this stage, production is moving forward but part arrival is not yet confirmed. Run Sentinelle to verify.")


            # Progress timeline
            st.markdown("---")
            st.markdown("#### 🎬 Simulated production flow progress")
            hours = output2.get("hours_elapsed", 0)
            sim_cols = st.columns(len(ROUTING))
            for i, (col, op) in enumerate(zip(sim_cols, ROUTING)):
                if hours >= op["cumulative_end_hours"]:
                    col.markdown(f"✅ **{op['operationId'][:4]}**")
                    col.caption("Completed")
                elif hours >= op["cumulative_start_hours"]:
                    col.markdown(f"🟠 **{op['operationId'][:4]}**")
                    col.caption("In progress")
                elif output2.get("blocked") and output2.get("blocked_at") and op["operationId"] == output2["blocked_at"]["operationId"]:
                    col.markdown(f"🔴 **{op['operationId'][:4]}**")
                    col.caption("Blocking point reached")
                else:
                    col.markdown(f"⚪ {op['operationId'][:4]}")
                    col.caption("Upcoming")


            # Waiting parts (information only)
            if output2.get("waiting_parts"):
                st.markdown("**⏳ Components awaiting delivery**")
                for p in output2["waiting_parts"]:
                    if p["days_remaining"] > 0:
                        st.markdown(f"- ⏳ {p['itemCode']} × {p['qty_ordered']} ({p['supplier']}, {p['days_remaining']}d remaining)")
                    else:
                        st.markdown(f"- 📦 {p['itemCode']} × {p['qty_ordered']} ({p['supplier']}, ETA reached — run Sentinelle)")


        else:
            # Standard Sentinelle
            ev_col1, ev_col2, ev_col3, ev_col4 = st.columns(4)
            risk_icons = {"VERT": "🟢", "ORANGE": "🟠", "ROUGE": "🔴"}
            init_risk = output2.get("initial_risk_level", "?")
            curr_risk = output2.get("current_risk_level", "?")
            evolution = output2.get("risk_evolution", "?")
            warning = output2.get("warning_status", "?")


            ev_col1.metric("Initial risk", f"{risk_icons.get(init_risk, '⚪')} {init_risk}")
            ev_col2.metric("Current risk", f"{risk_icons.get(curr_risk, '⚪')} {curr_risk}")
            ev_icons = {"BAISSE": "📉", "STABLE": "➡️", "HAUSSE": "📈"}
            ev_col3.metric("Trend", f"{ev_icons.get(evolution, '?')} {evolution}")
            w_icons = {"LEVE": "✅", "CONFIRME": "🔴", "EN_SURVEILLANCE": "🔍"}
            ev_col4.metric("Alert", f"{w_icons.get(warning, '?')} {warning}")


            if warning == "LEVE":
                st.success(f"✅ **Risk cleared** — {output2['sentinelle_message']}")
            elif warning == "CONFIRME":
                st.error(f"🔴 **Risk confirmed** — {output2['sentinelle_message']}")
            else:
                st.warning(f"🔍 **Risk under monitoring** — {output2['sentinelle_message']}")


            # ── Part tracking ──
            tracking = output2.get("parts_tracking", [])
            if tracking:
                st.markdown("---")
                st.markdown("#### 📦 Detailed component tracking")
                track_rows = []
                for pt in tracking:
                    status_icons = {"REÇU": "✅", "EN_ATTENTE": "⏳", "MANQUANT": "❌"}
                    track_rows.append({
                        "Component": pt["itemCode"],
                        "Status": f"{status_icons.get(pt['current_status'], '?')} {pt['current_status']}",
                        "Supplier": pt.get("supplier", "—"),
                        "Initial ETA": pt.get("eta_initial", "—"),
                        "Updated ETA": pt.get("eta_updated", "—"),
                        "Qty received": pt.get("qty_received", 0),
                    })
                st.dataframe(pd.DataFrame(track_rows), use_container_width=True, hide_index=True)


            # ── Updated impact ──
            st.markdown("---")
            st.markdown("#### 📅 Updated impact on the production order")


            imp_col1, imp_col2, imp_col3 = st.columns(3)
            imp_col1.metric("Estimated completion date", output2.get("updated_eta_end", "—"))
            imp_col1.caption("Estimate: launch date + production duration + supplier delay impact.")
            imp_col2.metric("Updated delay", f"+{output2.get('updated_delay_days', 0)} d")
            imp_col2.caption("Estimate: revised completion date minus customer due date.")
            imp_col3.metric("Business priority", f"{output2.get('resume_priority', '?')}/5")
            imp_col3.caption("The lower the score, the faster the production order must be handled.")


        # ── Comparison with/without AI ──
        st.markdown("---")
        st.markdown("#### 🔀 Comparison: with AI-driven control vs without AI-driven control")


        maestro_delay = m_ref.get("estimated_delay_days", 0)
        if source_type == "simulation":
            actual_delay = maestro_delay
        else:
            actual_delay = output2.get("updated_delay_days", 0)


        comp_data = {
            "Scenario": [
                "Control with AI recommendations",
                "Initial plan without AI adjustment",
            ],
            "Estimated delay": [
                f"+{actual_delay} d" if actual_delay > 0 else "None",
                f"+{maestro_delay} d" if maestro_delay > 0 else "Not quantified",
            ],
        }
        st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)


        # ── Plan B ──
        if source_type == "sentinelle" and output2.get("plan_b_needed"):
            st.markdown("---")
            st.markdown("#### 🚨 Plan B — Rescheduling required")
            prop = output2.get("rescheduling_proposal")
            if prop:
                st.error(
                    f"🔄 **{prop['label']}**\n"
                    f"- Launch: {prop['launch_date']}\n"
                    f"- Estimated completion: {prop['estimated_completion']}\n"
                    f"- Delay: +{prop['delay_client_days']}d — Penalties: {prop['penalty_eur']:,.0f} €"
                )
        elif source_type == "simulation" and output2.get("blocked"):
            st.markdown("---")
            st.markdown("#### 🚨 Blocking point reached — Rescheduling to be instructed")
            resch = m_ref.get("rescheduling_options", [])
            if resch:
                for opt in resch:
                    st.warning(
                        f"🔄 **{opt['label']}** — delay +{opt['delay_client_days']}d, "
                        f"penalties {opt['penalty_eur']:,.0f}€"
                    )
        else:
            st.success("✅ No Plan B needed at this stage — situation under control.")


        # ── Prompts and JSON ──
        if source_type == "sentinelle":
            _s_prompt = build_live_context_sentinelle(
                selected_of2, order2.get("priority", "?"), order2.get("dueDate", "?")[:10],
                m_ref, order2["stock"],
                output2.get("still_missing_components", []), output2.get("resolved_components", []),
            )
            with st.expander("📝 Prompt sent to Sentinelle"):
                st.code(SENTINELLE_SYSTEM_PROMPT, language="markdown")
                st.code(_s_prompt, language="markdown")


        with st.expander("🔧 Technical JSON"):
            st.json(output2)
