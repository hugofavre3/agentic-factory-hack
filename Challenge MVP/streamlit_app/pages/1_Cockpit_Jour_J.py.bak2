"""Page 1 — Cockpit d'anticipation des retards.

Objectif : en un coup d'œil, voir où je risque d'être en retard,
à quel stade de la production, et pourquoi.
Inclut les données d'entrée (inputs) accessibles par boutons.
"""

import streamlit as st
import pandas as pd
import sys, os
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data import (
    run_maestro, run_orchestrator, run_sentinelle, build_seed_orders,
    apply_operator_decision,
    BOM_FULL, DEFAULT_STOCK, ROUTING, SUPPLIERS_DATA,
    HISTORICAL_OFS_DATA, MACHINE_CALENDAR_DATA, SLA_RULES_DATA,
    _check_availability, _find_cutoff, _find_last_doable, _find_risk_steps,
    build_live_context_maestro, build_live_context_sentinelle,
    MAESTRO_SYSTEM_PROMPT, SENTINELLE_SYSTEM_PROMPT,
    call_llm, get_stock_updates_preview, resume_of,
    WORK_HOURS_PER_DAY,
)

st.set_page_config(page_title="Cockpit d'anticipation", page_icon="📋", layout="wide")

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

# =============================================================================
# Titre
# =============================================================================

st.title("📋 Cockpit d'anticipation des retards")
st.markdown(
    "*En un coup d'œil : quels OF risquent d'être en retard, à quelle étape, et pourquoi. "
    "Maestro anticipe, Sentinelle surveille.*"
)

# =============================================================================
# Bandeau KPIs
# =============================================================================

st.divider()

maestro_outs = st.session_state["maestro_outputs"]
sentinelle_outs = st.session_state["sentinelle_outputs"]

total_of = len(sim_orders)

# OF à risque (ORANGE ou ROUGE)
of_at_risk = sum(
    1 for of_id in sim_orders
    if maestro_outs.get(of_id, {}).get("risk_level") in ("ORANGE", "ROUGE")
)

# OF sous contrôle (VERT ou risque levé par Sentinelle)
of_ok = sum(
    1 for of_id in sim_orders
    if maestro_outs.get(of_id, {}).get("risk_level") == "VERT"
    or sentinelle_outs.get(of_id, {}).get("warning_status") == "LEVE"
)

# Retard cumulé évité (jours estimés évités grâce aux recommandations)
delay_avoided = sum(
    maestro_outs.get(of_id, {}).get("estimated_delay_days", 0)
    for of_id in sim_orders
    if sentinelle_outs.get(of_id, {}).get("warning_status") == "LEVE"
)

k1, k2, k3, k4 = st.columns(4)
k1.metric("⚠️ OF à risque de retard", of_at_risk, help="OF avec risque ORANGE ou ROUGE")
k2.metric("✅ OF sous contrôle", of_ok, help="Risque VERT ou warning levé par Sentinelle")
k3.metric("⏱️ Retard évité (estimé)", f"{delay_avoided} j", help="Jours de retard évités par les recommandations Maestro")
k4.metric("📦 Total OF", total_of)

# =============================================================================
# Données d'entrée (Inputs) — avec boutons d'exploration
# =============================================================================

st.divider()
st.subheader("📂 Données d'entrée")
st.caption("Les données utilisées par Maestro et Sentinelle pour analyser les risques.")

inp_col1, inp_col2, inp_col3, inp_col4 = st.columns(4)

with inp_col1:
    with st.expander("📦 Stock actuel"):
        stock_rows = []
        for comp in BOM_FULL:
            default_qty = DEFAULT_STOCK.get(comp["itemCode"], 0)
            crit = "🔴" if comp["isCritical"] else "⚪"
            stock_rows.append({
                "Composant": comp["itemCode"],
                "Description": comp["description"],
                "Stock": default_qty,
                "Critique": crit,
            })
        st.dataframe(pd.DataFrame(stock_rows), use_container_width=True, hide_index=True)

with inp_col2:
    with st.expander("🔧 Gamme (étapes)"):
        routing_rows = []
        for op in ROUTING:
            days = round(op["cumulative_start_hours"] / WORK_HOURS_PER_DAY, 1)
            routing_rows.append({
                "Séq.": op["sequence"],
                "Opération": op["operationId"],
                "Description": op["description"],
                "Durée (h)": op["duration_hours"],
                "Atteint en (j)": days,
                "Composants": ", ".join(op["requiredComponents"]) or "—",
            })
        st.dataframe(pd.DataFrame(routing_rows), use_container_width=True, hide_index=True)

with inp_col3:
    with st.expander("🚚 Fournisseurs"):
        sup_rows = []
        for s in SUPPLIERS_DATA:
            sup_rows.append({
                "Fournisseur": s["name"],
                "Composants": ", ".join(s["components"]),
                "Délai (j)": s["leadTime_days"],
                "Fiabilité": f"{s['reliability']*100:.0f}%",
                "Prix unit.": f"{s['unitPrice_eur']}€",
            })
        st.dataframe(pd.DataFrame(sup_rows), use_container_width=True, hide_index=True)

with inp_col4:
    with st.expander("📋 BOM (nomenclature)"):
        bom_rows = []
        for comp in BOM_FULL:
            bom_rows.append({
                "Code": comp["itemCode"],
                "Description": comp["description"],
                "Qté/unité": comp["qtyPerUnit"],
                "Critique": "🔴 Oui" if comp["isCritical"] else "Non",
            })
        st.dataframe(pd.DataFrame(bom_rows), use_container_width=True, hide_index=True)

# Ligne 2 d'inputs
inp2_col1, inp2_col2, inp2_col3 = st.columns(3)

with inp2_col1:
    with st.expander("📊 Historique OF"):
        hist_rows = []
        for h in HISTORICAL_OFS_DATA:
            hist_rows.append({
                "OF": h["of_id"],
                "Qté": h["quantity"],
                "Retard (j)": h["daysLate"],
                "Bloqué à": h.get("blockedAtStep") or "—",
                "Composants bloquants": ", ".join(h["blockedComponents"]) or "—",
            })
        st.dataframe(pd.DataFrame(hist_rows), use_container_width=True, hide_index=True)

with inp2_col2:
    with st.expander("🗓️ Calendrier machine"):
        cal_rows = []
        for slot in MACHINE_CALENDAR_DATA:
            cal_rows.append({
                "Créneau": slot["slotId"],
                "Date": slot["date"],
                "Shift": slot["shift"],
                "Charge": f"{slot['currentLoad']*100:.0f}%",
                "Statut": slot["status"],
            })
        st.dataframe(pd.DataFrame(cal_rows), use_container_width=True, hide_index=True)

with inp2_col3:
    with st.expander("📜 Règles SLA"):
        sla_rows = []
        for rule in SLA_RULES_DATA:
            sla_rows.append({
                "Client": rule["client"],
                "Niveau": rule["serviceLevelAgreement"],
                "Retard max": f"{rule['maxAcceptableDelay_days']} j",
                "Pénalité": f"{rule['penaltyPerDayLate_eur']}€/j",
            })
        st.dataframe(pd.DataFrame(sla_rows), use_container_width=True, hide_index=True)


# =============================================================================
# Tableau central — OF et risques par étape
# =============================================================================

st.divider()
st.subheader("📊 OF et risques par étape")

rows = []
for of_id, order in sim_orders.items():
    m = maestro_outs.get(of_id, {})
    s = sentinelle_outs.get(of_id, {})

    risk_level = m.get("risk_level", "—")
    etape = m.get("etape_a_risque")
    etape_label = etape["operationId"] if etape else "Aucune"
    prob_blocage = m.get("probabilite_blocage_pct", "—")
    delay = m.get("estimated_delay_days", "—")

    # Status Maestro
    action = m.get("recommended_action", "—")
    action_labels = {
        "LANCER_IMMEDIAT": "✅ Lancer",
        "LANCER_DECALE": "⚠️ Décaler",
        "REPORTER_ET_REPLANIFIER": "🛑 Reporter",
    }
    maestro_status = action_labels.get(action, "🔵 Non analysé")

    # Status Sentinelle
    warning = s.get("warning_status")
    sentinelle_status_labels = {
        "LEVE": "✅ Risque levé",
        "CONFIRME": "🔴 Risque confirmé",
        "EN_SURVEILLANCE": "🔍 En surveillance",
    }
    sentinelle_status = sentinelle_status_labels.get(warning, "—")

    # Risque icon
    risk_icons = {"VERT": "🟢", "ORANGE": "🟠", "ROUGE": "🔴"}
    risk_icon = risk_icons.get(risk_level, "⚪")

    # Jours restants
    due_dt = datetime.fromisoformat(order["dueDate"].replace("Z", "+00:00"))
    days_left = (due_dt - datetime.now(timezone.utc)).days

    rows.append({
        "OF": order["orderNumber"],
        "Produit": order["productCode"],
        "Qté": order["quantity"],
        "Échéance": order["dueDate"][:10],
        "J restants": days_left,
        "Risque": f"{risk_icon} {risk_level}",
        "Étape à risque": etape_label,
        "Prob. blocage": f"{prob_blocage}%" if isinstance(prob_blocage, (int, float)) else prob_blocage,
        "Retard estimé": f"{delay} j" if isinstance(delay, (int, float)) else delay,
        "Maestro": maestro_status,
        "Sentinelle": sentinelle_status,
    })

if rows:
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.info("Aucun OF chargé.")


# =============================================================================
# Sélection d'un OF + Analyse
# =============================================================================

st.divider()
st.subheader("⚡ Analyser un OF")

left, right = st.columns([1, 2])

with left:
    st.markdown("**Sélectionner un scénario**")

    scenario_labels = {of["of_id"]: of["scenario_label"] for of in sim_orders.values()}
    selected_of_id = st.radio(
        "Choisir un OF :",
        options=list(scenario_labels.keys()),
        format_func=lambda x: scenario_labels[x],
        label_visibility="collapsed",
    )

    selected_order = orders[selected_of_id]

    st.markdown("---")
    st.markdown(f"**OF : `{selected_order['orderNumber']}`**")
    st.markdown(f"- Produit : `{selected_order['productCode']}`")
    st.markdown(f"- Quantité : **{selected_order['quantity']}**")
    st.markdown(f"- Priorité : **{selected_order['priority']}**")

    due_dt = datetime.fromisoformat(selected_order["dueDate"].replace("Z", "+00:00"))
    _days_left = (due_dt - datetime.now(timezone.utc)).days
    _due_icon = "🔴" if _days_left < 10 else "🟠" if _days_left < 20 else "🟢"
    st.markdown(f"- Échéance : **{selected_order['dueDate'][:10]}** — {_due_icon} **{_days_left} j**")

    st.markdown("---")
    st.markdown("**Stock pour cet OF**")
    stock_df = pd.DataFrame([
        {"Composant": k, "Dispo": v, "Besoin": next(
            (c["qtyPerUnit"] * selected_order["quantity"]
             for c in selected_order["components"] if c["itemCode"] == k), 0
        )}
        for k, v in selected_order["stock"].items()
    ])
    stock_df["Manque"] = (stock_df["Besoin"] - stock_df["Dispo"]).clip(lower=0)
    stock_df["État"] = stock_df.apply(lambda r: "✅" if r["Dispo"] >= r["Besoin"] else "❌", axis=1)
    st.dataframe(stock_df, use_container_width=True, hide_index=True)


with right:

    # ─── Maestro ────────────────────────────────────────────────
    st.markdown("#### 🎼 Maestro — Analyse de risque et recommandation")
    st.caption(
        "*Maestro vérifie : si je lance maintenant, est-ce que la production "
        "atteindra l'étape critique avant que les pièces n'arrivent ?*"
    )

    if st.button("🎼 Lancer l'analyse Maestro", key="btn_maestro", type="primary"):
        output = run_maestro(selected_of_id, orders)
        st.session_state["maestro_outputs"][selected_of_id] = output

    # ── Affichage Maestro ───────────────────────────────────
    if selected_of_id in st.session_state["maestro_outputs"]:
        output = st.session_state["maestro_outputs"][selected_of_id]
        risk = output["risk_level"]
        score = output["global_risk_score"]
        action = output["recommended_action"]
        prob = output["probabilite_blocage_pct"]
        delay = output["estimated_delay_days"]
        penalty = output["estimated_penalty_eur"]
        etape = output.get("etape_a_risque")

        # ── Barre de risque ──
        risk_colors = {"VERT": "success", "ORANGE": "warning", "ROUGE": "error"}
        risk_icons = {"VERT": "🟢", "ORANGE": "🟠", "ROUGE": "🔴"}
        st.markdown(f"##### {risk_icons.get(risk, '⚪')} Risque : **{risk}** (score {score}/100)")

        if etape:
            st.info(
                f"📍 **Étape à risque** : {etape['operationId']} ({etape['description']}) — "
                f"atteinte en **{etape['time_to_reach_days']} jours**. "
                f"Composant manquant : **{etape['composant_manquant']}**."
            )

        # ── Métriques ──
        rc1, rc2, rc3, rc4 = st.columns(4)
        rc1.metric("Prob. blocage", f"{prob}%")
        rc2.metric("Retard estimé", f"{delay} j")
        rc3.metric("Pénalités", f"{penalty:,.0f} €")
        rc4.metric("J avant échéance", f"{output.get('days_until_due', '?')} j")

        # ── Recommandation ──
        st.markdown("##### 💡 Recommandation Maestro")
        action_labels = {
            "LANCER_IMMEDIAT": ("✅", "Lancer immédiatement"),
            "LANCER_DECALE": ("⚠️", "Lancer en décalé"),
            "REPORTER_ET_REPLANIFIER": ("🛑", "Reporter et replanifier"),
        }
        a_icon, a_label = action_labels.get(action, ("?", action))

        if action == "LANCER_IMMEDIAT":
            st.success(f"{a_icon} **{a_label}** — Pas de retard attendu, on lance comme prévu.")
        elif action == "LANCER_DECALE":
            launch_date = output.get("recommended_launch_date", "?")
            slot = output.get("recommended_launch_slot", "?")
            st.warning(
                f"{a_icon} **{a_label}** — Lancer le **{launch_date}** (créneau {slot}). "
                f"Garde un œil sur le risque."
            )
        else:
            st.error(f"{a_icon} **{a_label}** — Ne pas lancer maintenant.")
            opts = output.get("rescheduling_options", [])
            if opts:
                st.markdown("**Créneaux de reprogrammation proposés :**")
                for opt in opts:
                    st.markdown(
                        f"- **{opt['label']}** — fin estimée {opt['estimated_completion']}, "
                        f"retard client +{opt['delay_client_days']}j, pénalités {opt['penalty_eur']:,.0f}€\n"
                        f"  *{opt['comment']}*"
                    )

        # ── Message Maestro ──
        st.markdown(f"💬 *{output['maestro_message']}*")

        # ── Notification fournisseur ──
        emails = output.get("simulated_emails", [])
        if emails:
            st.markdown("---")
            st.markdown("##### 📧 Notification fournisseur envoyée")
            for email in emails:
                st.success(f"📧 Mail envoyé à **{email['to_name']}** ({email['to']})")
                with st.expander(f"📨 Voir le mail — {email['subject']}"):
                    st.markdown(f"**À** : {email['to']}")
                    st.markdown(f"**Objet** : {email['subject']}")
                    st.markdown("---")
                    st.text(email["body"])

        # ── Plan fournisseur ──
        plan = output.get("supplier_order_plan", [])
        if plan:
            with st.expander("📦 Plan de commande fournisseur"):
                st.dataframe(pd.DataFrame(plan), use_container_width=True, hide_index=True)

        # ── Détails techniques ──
        if output.get("reasoning"):
            with st.expander("💬 Explication détaillée"):
                st.write(output["reasoning"])

        if output.get("risk_factors"):
            with st.expander("📊 Facteurs de risque"):
                st.dataframe(pd.DataFrame(output["risk_factors"]), use_container_width=True, hide_index=True)

        with st.expander("🔧 JSON technique"):
            st.json(output)

        # ── Film de production ──
        st.markdown("---")
        st.markdown("##### 🎬 Film de production — étapes et point de risque")

        missing_codes = {mc["itemCode"] for mc in output.get("missing_components", [])}
        prog_cols = st.columns(len(ROUTING))
        for i, (col, op) in enumerate(zip(prog_cols, ROUTING)):
            blocked = set(op.get("requiredComponents", [])) & missing_codes
            days = round(op["cumulative_start_hours"] / WORK_HOURS_PER_DAY, 1)
            is_risk_step = etape and op["operationId"] == etape["operationId"]

            if is_risk_step:
                col.markdown(f"🔴 **{op['operationId'][:4]}**")
                col.caption(f"⚠️ {days}j")
            elif blocked:
                col.markdown(f"🟠 **{op['operationId'][:4]}**")
                col.caption(f"{days}j")
            else:
                col.markdown(f"🟢 {op['operationId'][:4]}")
                col.caption(f"{days}j")

        # ── Décision opérateur ──────────────────────────────────
        st.markdown("---")
        if output.get("operator_decision"):
            op_dec = output["operator_decision"]
            dec_label = action_labels.get(op_dec, ("?", op_dec))[1]
            agreed = "✅ (conforme Maestro)" if op_dec == action else "⚡ (override)"
            st.success(f"🎯 **Décision opérateur : {dec_label}** {agreed}")
            st.markdown(f"**Consigne** : {output.get('instruction', '—')}")
        else:
            st.markdown("##### 🎯 Votre décision")
            st.caption("*Maestro recommande, vous décidez.*")

            decision_options = ["LANCER_IMMEDIAT", "LANCER_DECALE", "REPORTER_ET_REPLANIFIER"]
            decision_labels = {
                "LANCER_IMMEDIAT": "✅ Lancer immédiatement",
                "LANCER_DECALE": "⚠️ Lancer en décalé",
                "REPORTER_ET_REPLANIFIER": "🛑 Reporter et replanifier",
            }
            default_idx = decision_options.index(action) if action in decision_options else 0

            chosen = st.radio(
                "Action :",
                options=decision_options,
                format_func=lambda x: f"{decision_labels[x]} {'★ Recommandé' if x == action else ''}",
                index=default_idx,
                key=f"radio_{selected_of_id}",
                horizontal=True,
            )

            if chosen != action:
                st.warning(f"⚡ Vous vous écartez de la recommandation Maestro ({a_label}).")

            if st.button("✅ Valider la décision", key=f"btn_validate_{selected_of_id}", type="primary"):
                instruction = apply_operator_decision(
                    selected_of_id, orders, st.session_state["maestro_outputs"], chosen
                )
                st.success(f"🎯 **Décision validée : {decision_labels[chosen]}**")
                st.markdown(f"**Consigne** : {instruction}")
                st.rerun()

    st.divider()

    # ─── Orchestrateur ──────────────────────────────────────────
    st.markdown("#### 🔗 Activer la surveillance Sentinelle (Orchestrateur)")
    st.caption("*Quels OF doivent être surveillés par Sentinelle ?*")

    if st.button("Mettre à jour la watchlist", key="btn_orch"):
        m_outputs = st.session_state["maestro_outputs"]
        if not m_outputs:
            st.warning("Lancez d'abord Maestro sur au moins un OF.")
        else:
            watchlist = run_orchestrator(m_outputs)
            st.session_state["watchlist"] = watchlist

            if watchlist:
                st.success(f"✅ {len(watchlist)} OF à surveiller par Sentinelle")
                st.dataframe(pd.DataFrame(watchlist), use_container_width=True, hide_index=True)
            else:
                st.info("Aucun OF à surveiller — tous les OF sont lancés immédiatement.")

    elif st.session_state["watchlist"]:
        st.markdown(f"**Watchlist Sentinelle** : {len(st.session_state['watchlist'])} OF")
        st.dataframe(pd.DataFrame(st.session_state["watchlist"]), use_container_width=True, hide_index=True)

    st.divider()

    # ─── Réception stock simulée ────────────────────────────────
    st.markdown("#### 📦 Réception stock simulée")
    st.caption("*Le temps passe. Des livraisons fournisseur arrivent.*")

    watchlist = st.session_state["watchlist"]
    if watchlist:
        previews = get_stock_updates_preview(orders, watchlist)
        for prev in previews:
            of_label = prev["orderNumber"]
            if prev["has_arrivals"]:
                arr_rows = [a for a in prev["arrivals"] if a["delta"] > 0]
                if arr_rows:
                    st.success(f"📦 **{of_label}** — Livraisons reçues :")
                    st.dataframe(
                        pd.DataFrame(arr_rows)[["itemCode", "stock_avant", "stock_après", "delta", "type"]],
                        use_container_width=True, hide_index=True,
                    )
            else:
                st.info(f"📭 **{of_label}** — Aucune livraison, stock inchangé.")
    else:
        st.caption("Activez d'abord l'orchestrateur.")

    st.divider()

    # ─── Sentinelle ─────────────────────────────────────────────
    st.markdown("#### 🔭 Sentinelle — Mise à jour du risque")
    st.caption("*Sentinelle vérifie si les hypothèses de Maestro se confirment.*")

    if st.button("🔭 Lancer Sentinelle", key="btn_sentinelle", type="primary"):
        watchlist = st.session_state["watchlist"]
        if not watchlist:
            st.warning("Watchlist vide — activez d'abord l'orchestrateur.")
        else:
            results = run_sentinelle(orders, st.session_state["maestro_outputs"], watchlist)
            for res in results:
                st.session_state["sentinelle_outputs"][res["of_id"]] = res

            for res in results:
                of_id = res["of_id"]
                warning = res["warning_status"]
                evolution = res["risk_evolution"]

                ev_icons = {"BAISSE": "📉", "STABLE": "➡️", "HAUSSE": "📈"}

                if warning == "LEVE":
                    st.success(
                        f"✅ **{orders[of_id]['orderNumber']}** — Risque **levé** {ev_icons.get(evolution, '')} "
                        f"{res['initial_risk_level']} → {res['current_risk_level']}"
                    )
                elif warning == "CONFIRME":
                    st.error(
                        f"🔴 **{orders[of_id]['orderNumber']}** — Risque **confirmé** {ev_icons.get(evolution, '')} "
                        f"Retard estimé : +{res.get('updated_delay_days', '?')} jours"
                    )
                else:
                    st.warning(
                        f"🔍 **{orders[of_id]['orderNumber']}** — En surveillance "
                        f"{ev_icons.get(evolution, '')}"
                    )

                st.markdown(f"💬 *{res['sentinelle_message']}*")

                # Suivi pièces
                if res.get("parts_tracking"):
                    with st.expander(f"📦 Suivi pièces — {orders[of_id]['orderNumber']}"):
                        st.dataframe(pd.DataFrame(res["parts_tracking"]), use_container_width=True, hide_index=True)

                # Plan B (worst case uniquement)
                if res.get("plan_b_needed") and res.get("rescheduling_proposal"):
                    prop = res["rescheduling_proposal"]
                    st.warning(
                        f"🔄 **Plan B** : {prop['label']} — "
                        f"retard client +{prop['delay_client_days']}j, pénalités {prop['penalty_eur']:,.0f}€"
                    )

                st.markdown(f"**Consigne** : {res['instruction']}")

                with st.expander(f"🔧 JSON — {orders[of_id]['orderNumber']}"):
                    st.json(res)

            st.session_state["watchlist"] = [
                w for w in watchlist
                if orders[w["of_id"]]["status"] not in ("RisqueLeve", "Released")
            ]

    st.divider()

    # ─── Reprendre la production (Plan B worst case) ───────────
    st.markdown("#### ▶️ Reprendre la production (Plan B — worst case)")
    st.caption("*Uniquement si, malgré l'anticipation, production stoppée.*")

    ready_ofs = {
        of_id: o for of_id, o in sim_orders.items()
        if o["status"] == "RisqueLeve"
    }
    if ready_ofs:
        for of_id, order in ready_ofs.items():
            col_btn, col_info = st.columns([1, 3])
            with col_btn:
                if st.button(f"▶️ Reprendre {order['orderNumber']}", key=f"btn_resume_{of_id}"):
                    resume_of(of_id, orders)
                    st.session_state["watchlist"] = [
                        w for w in st.session_state["watchlist"] if w["of_id"] != of_id
                    ]
                    st.success(f"✅ **{order['orderNumber']}** → **Lancé**")
                    st.rerun()
            with col_info:
                st.markdown(f"Risque levé — pièces disponibles")
    else:
        st.caption("Aucun OF en attente de reprise.")


# =============================================================================
# Focus OF — Messages Maestro & Sentinelle
# =============================================================================

st.divider()
st.subheader("🔎 Focus OF — Messages Maestro & Sentinelle")

focus_options = {of_id: o["orderNumber"] for of_id, o in sim_orders.items()}
focus_of_id = st.selectbox(
    "Sélectionner un OF :",
    options=list(focus_options.keys()),
    format_func=lambda x: focus_options[x],
    key="focus_of",
)

focus_order = orders[focus_of_id]
m_out = st.session_state["maestro_outputs"].get(focus_of_id, {})
s_out = st.session_state["sentinelle_outputs"].get(focus_of_id, {})

# Timeline
st.markdown("**Progression**")
has_decision = bool(m_out.get("operator_decision"))
if focus_order["status"] in ("Released",):
    current_step = 4
elif s_out:
    current_step = 3
elif has_decision:
    current_step = 2
elif m_out:
    current_step = 1
else:
    current_step = 0

steps = ["Créé", "Analyse Maestro", "Décision", "Suivi Sentinelle", "Terminé"]
cols_tl = st.columns(5)
for i, (col, step) in enumerate(zip(cols_tl, steps)):
    if i < current_step:
        col.markdown(f"✅ **{step}**")
    elif i == current_step:
        col.markdown(f"🔵 **{step}**")
    else:
        col.markdown(f"⚪ {step}")

# Messages
st.markdown("---")
col_m, col_s = st.columns(2)

with col_m:
    st.markdown("**🎼 Maestro**")
    if m_out:
        risk = m_out["risk_level"]
        risk_icon = {"VERT": "🟢", "ORANGE": "🟠", "ROUGE": "🔴"}.get(risk, "⚪")
        st.markdown(f"{risk_icon} Risque **{risk}** — Score {m_out['global_risk_score']}/100")
        st.markdown(f"*{m_out['maestro_message']}*")
        if m_out.get("operator_decision"):
            dec_labels = {
                "LANCER_IMMEDIAT": "Lancer immédiatement",
                "LANCER_DECALE": "Lancer en décalé",
                "REPORTER_ET_REPLANIFIER": "Reporter",
            }
            st.markdown(f"🎯 Décision : **{dec_labels.get(m_out['operator_decision'], m_out['operator_decision'])}**")
            st.markdown(f"Consigne : {m_out.get('instruction', '—')}")
    else:
        st.caption("Maestro n'a pas encore analysé cet OF.")

with col_s:
    st.markdown("**🔭 Sentinelle**")
    if s_out:
        w = s_out["warning_status"]
        w_icons = {"LEVE": "✅", "CONFIRME": "🔴", "EN_SURVEILLANCE": "🔍"}
        st.markdown(f"{w_icons.get(w, '?')} Warning **{w}** — {s_out['initial_risk_level']} → {s_out['current_risk_level']}")
        st.markdown(f"*{s_out['sentinelle_message']}*")
        if s_out.get("updated_delay_days", 0) > 0:
            st.markdown(f"Retard actualisé : **+{s_out['updated_delay_days']} jours**")
    else:
        st.caption("Sentinelle n'a pas encore vérifié cet OF.")
