"""Page 2 — Maestro & Sentinelle (Décisions et impacts).

Objectif : montrer l'impact sur le film de production et le retard.
Onglet Maestro : décision, graphique prod vs pièces, mail simulé.
Onglet Sentinelle : risque initial vs actuel, ETA actualisée, Plan B.
"""

import streamlit as st
import pandas as pd
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data import (
    build_seed_orders, ROUTING, WORK_HOURS_PER_DAY,
    _check_availability, _find_cutoff, _find_last_doable,
    build_live_context_maestro, build_live_context_sentinelle,
    MAESTRO_SYSTEM_PROMPT, SENTINELLE_SYSTEM_PROMPT,
)

st.set_page_config(page_title="Maestro & Sentinelle", page_icon="🧠", layout="wide")

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

st.title("🧠 Maestro & Sentinelle — Décisions et impacts")
st.markdown(
    "*Comprendre pourquoi l'IA recommande tel créneau de lancement, "
    "et comment Sentinelle met à jour le risque en temps réel.*"
)

st.divider()

# =============================================================================
# Onglets
# =============================================================================

tab1, tab2 = st.tabs([
    "🎼 Maestro — Stratégie de lancement",
    "🔭 Sentinelle — Surveillance et actualisation",
])

# =============================================================================
# Onglet Maestro
# =============================================================================

with tab1:
    st.markdown("### 🎼 Maestro : Comment lancer cet OF ?")
    st.caption(
        "Maestro croise étapes de production, temps de traversée, stock et délais fournisseurs "
        "pour répondre : *\"Si je lance, y a-t-il un risque de blocage avant l'arrivée des pièces ?\"*"
    )

    m_outputs = st.session_state["maestro_outputs"]

    if not m_outputs:
        st.info("Aucune analyse Maestro. Allez dans le **Cockpit** et lancez Maestro sur un OF.")
    else:
        m_keys = [k for k in m_outputs if k in orders]
        selected_of = st.selectbox(
            "Sélectionner un OF :",
            options=m_keys,
            format_func=lambda x: f"{orders[x]['orderNumber']} — {orders[x]['scenario_label']}",
            key="m_select",
        )

        output = m_outputs[selected_of]
        order = orders[selected_of]

        # ── Résumé décision ──────────────────────────────────
        st.markdown("---")

        op_dec = output.get("operator_decision")
        if op_dec:
            st.markdown("#### Décision validée par l'opérateur")
        else:
            st.markdown("#### Recommandation Maestro (en attente de validation)")

        action = output.get("operator_decision") or output.get("recommended_action", "?")
        risk = output["risk_level"]
        score = output["global_risk_score"]

        action_labels = {
            "LANCER_IMMEDIAT": ("✅ Lancer immédiatement", "Tous les composants disponibles, aucun risque de blocage."),
            "LANCER_DECALE": ("⚠️ Lancer en décalé", "Risque gérable — lancer à un créneau décalé pour que les pièces arrivent à temps."),
            "REPORTER_ET_REPLANIFIER": ("🛑 Reporter et replanifier", "Risque trop élevé — reporter l'OF et choisir un créneau plus sûr."),
        }
        label, desc = action_labels.get(action, ("?", ""))

        c1, c2, c3 = st.columns(3)
        c1.metric("Décision", label.split("—")[0].strip() if "—" in label else label)
        c2.metric("Score de risque", f"{score}/100")
        launch_date = output.get("recommended_launch_date") or "—"
        c3.metric("Date de lancement", launch_date)

        risk_icons = {"VERT": "🟢", "ORANGE": "🟠", "ROUGE": "🔴"}
        if action == "LANCER_IMMEDIAT":
            st.success(f"{risk_icons.get(risk, '⚪')} {label} — {desc}")
        elif action == "LANCER_DECALE":
            st.warning(f"{risk_icons.get(risk, '⚪')} {label} — {desc}")
        else:
            st.error(f"{risk_icons.get(risk, '⚪')} {label} — {desc}")

        st.markdown(f"**Consigne atelier** : {output.get('instruction', '⏳ En attente de décision')}")

        # ── Créneau proposé et retard estimé ─────────────────
        st.markdown("---")
        st.markdown("#### ⏱️ Impact sur le planning")

        ic1, ic2, ic3, ic4 = st.columns(4)
        ic1.metric("Prob. blocage", f"{output['probabilite_blocage_pct']}%")
        ic2.metric("Retard estimé", f"{output['estimated_delay_days']} j")
        ic3.metric("Pénalités", f"{output['estimated_penalty_eur']:,.0f} €")
        ic4.metric("Durée prod.", f"{output.get('estimated_production_days', '?')} j")

        if output.get("sla_impact"):
            st.caption(f"📋 **SLA** : {output['sla_impact']}")

        # ── Graphique : Production vs Arrivée pièces ─────────
        st.markdown("---")
        st.markdown("#### 📈 Avance de production vs fenêtre d'arrivée des pièces")

        etape = output.get("etape_a_risque")
        if etape and output.get("supplier_order_plan"):
            # Données pour le graphique
            plan = output["supplier_order_plan"]
            relevant_plan = [p for p in plan if p["itemCode"] == etape["composant_manquant"]]
            supplier_eta_days = relevant_plan[0]["estimated_lead_days"] if relevant_plan else None

            # Construire les lignes du graphique simplifié
            steps_data = []
            for op in ROUTING:
                day = round(op["cumulative_start_hours"] / WORK_HOURS_PER_DAY, 1)
                steps_data.append({
                    "Étape": op["operationId"],
                    "Jour (prod.)": day,
                    "Description": op["description"],
                })

            col_chart, col_legend = st.columns([3, 1])

            with col_chart:
                chart_df = pd.DataFrame(steps_data)
                chart_df["Production"] = chart_df["Jour (prod.)"]

                if supplier_eta_days:
                    chart_df["ETA pièce"] = supplier_eta_days
                    st.line_chart(chart_df.set_index("Étape")[["Production", "ETA pièce"]])
                else:
                    st.line_chart(chart_df.set_index("Étape")[["Production"]])

            with col_legend:
                st.markdown("**Légende**")
                st.markdown("📈 **Production** : progression dans la gamme (jours)")
                if supplier_eta_days:
                    st.markdown(f"📦 **ETA pièce** : {etape['composant_manquant']} arrive en {supplier_eta_days}j")
                st.markdown(f"⚠️ **Zone critique** : quand la courbe de production croise l'ETA")

                if supplier_eta_days and etape['time_to_reach_days'] < supplier_eta_days:
                    st.error(f"⚠️ Production atteint {etape['operationId']} en {etape['time_to_reach_days']}j, pièce arrive en {supplier_eta_days}j")
                elif supplier_eta_days:
                    st.success(f"✅ Pièce arrive ({supplier_eta_days}j) avant l'étape ({etape['time_to_reach_days']}j)")

        elif not etape:
            st.success("✅ Aucune étape à risque — tous les composants sont disponibles.")
        else:
            st.info("Pas de graphique disponible — aucun plan fournisseur.")

        # ── Créneaux de reprogrammation (si critique) ───────
        opts = output.get("rescheduling_options", [])
        if opts:
            st.markdown("---")
            st.markdown("#### 🔄 Créneaux de reprogrammation proposés")
            opts_rows = []
            for opt in opts:
                opts_rows.append({
                    "Créneau": opt["label"],
                    "Lancement": opt["launch_date"],
                    "Fin estimée": opt["estimated_completion"],
                    "Retard client": f"+{opt['delay_client_days']} j",
                    "Pénalités": f"{opt['penalty_eur']:,.0f} €",
                    "Commentaire": opt["comment"],
                })
            st.dataframe(pd.DataFrame(opts_rows), use_container_width=True, hide_index=True)

        # ── Action fournisseur simulée ────────────────────────
        emails = output.get("simulated_emails", [])
        if emails:
            st.markdown("---")
            st.markdown("#### 📧 Actions fournisseur simulées")
            for email in emails:
                st.success(f"📧 **Notification envoyée** à {email['to_name']} ({email['to']})")
                with st.expander(f"Voir le mail — {email['subject']}"):
                    st.markdown(f"**Destinataire** : {email['to_name']} <{email['to']}>")
                    st.markdown(f"**Objet** : {email['subject']}")
                    st.markdown("---")
                    st.text(email["body"])

        # ── Explication IA ──────────────────────────────────────
        if output.get("reasoning"):
            st.markdown("---")
            st.markdown("#### 💬 Explication détaillée")
            st.write(output["reasoning"])

        # ── Facteurs de risque ──────────────────────────────────
        st.markdown("---")
        st.markdown("#### 📋 Pourquoi ce choix ?")

        # Stock
        st.markdown("**Stock actuel pour cet OF**")
        stock_rows = []
        for comp in order["components"]:
            needed = comp["qtyPerUnit"] * order["quantity"]
            avail = order["stock"].get(comp["itemCode"], 0)
            crit = "🔴 Critique" if comp.get("isCritical") else ""

            # Trouver l'étape associée
            step = "—"
            for op in ROUTING:
                if comp["itemCode"] in op.get("requiredComponents", []):
                    step = op["operationId"]
                    break

            stock_rows.append({
                "Composant": comp["itemCode"],
                "Besoin": needed,
                "Dispo": avail,
                "Étape": step,
                "État": "✅" if avail >= needed else "❌",
                "Critique": crit,
            })
        st.dataframe(pd.DataFrame(stock_rows), use_container_width=True, hide_index=True)

        if output.get("risk_factors"):
            st.markdown("**Facteurs de risque**")
            st.dataframe(pd.DataFrame(output["risk_factors"]), use_container_width=True, hide_index=True)

        # ── Gamme ────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("#### 🔧 Gamme de fabrication avec timing")
        missing_codes = {mc["itemCode"] for mc in output.get("missing_components", [])}
        routing_rows = []
        for op in ROUTING:
            blocked = set(op.get("requiredComponents", [])) & missing_codes
            days = round(op["cumulative_start_hours"] / WORK_HOURS_PER_DAY, 1)
            routing_rows.append({
                "Séq.": op["sequence"],
                "Opération": op["operationId"],
                "Description": op["description"],
                "Composants": ", ".join(op.get("requiredComponents", [])) or "—",
                "Atteint en": f"{days} j",
                "Durée": f"{op['duration_hours']}h",
                "État": "🔴 Bloqué" if blocked else "🟢 OK",
            })
        st.dataframe(pd.DataFrame(routing_rows), use_container_width=True, hide_index=True)

        # ── Prompts et JSON ──────────────────────────────────
        _missing = _check_availability(order["components"], order["quantity"], order["stock"])
        _cutoff = _find_cutoff(ROUTING, _missing)
        _last = _find_last_doable(ROUTING, _cutoff)
        _prompt = build_live_context_maestro(order, order["stock"], _missing, _cutoff, _last)

        with st.expander("📝 Prompt envoyé à Maestro"):
            st.code(MAESTRO_SYSTEM_PROMPT, language="markdown")
            st.code(_prompt, language="markdown")

        with st.expander("🔧 JSON technique"):
            st.json(output)


# =============================================================================
# Onglet Sentinelle
# =============================================================================

with tab2:
    st.markdown("### 🔭 Sentinelle : Surveillance et actualisation du risque")
    st.caption(
        "Sentinelle reçoit la watchlist de Maestro et surveille en continu : "
        "les entrées en stock, les confirmations fournisseurs, l'avancement de la production. "
        "Son objectif : lever les warnings dès que possible."
    )

    s_outputs = st.session_state["sentinelle_outputs"]

    if not s_outputs:
        st.info("Aucune analyse Sentinelle. Allez dans le **Cockpit** et lancez Sentinelle.")
    else:
        s_keys = [k for k in s_outputs if k in orders]
        selected_of2 = st.selectbox(
            "Sélectionner un OF :",
            options=s_keys,
            format_func=lambda x: f"{orders[x]['orderNumber']} — {orders[x]['scenario_label']}",
            key="s_select",
        )

        output2 = s_outputs[selected_of2]
        order2 = orders[selected_of2]
        m_ref = st.session_state["maestro_outputs"].get(selected_of2, {})

        # ── Résumé : risque initial vs actuel ─────────────────
        st.markdown("---")
        st.markdown("#### 📊 Évolution du risque")

        ev_col1, ev_col2, ev_col3, ev_col4 = st.columns(4)

        risk_icons = {"VERT": "🟢", "ORANGE": "🟠", "ROUGE": "🔴"}
        init_risk = output2.get("initial_risk_level", "?")
        curr_risk = output2.get("current_risk_level", "?")
        evolution = output2.get("risk_evolution", "?")
        warning = output2.get("warning_status", "?")

        ev_col1.metric("Risque initial", f"{risk_icons.get(init_risk, '⚪')} {init_risk}")
        ev_col2.metric("Risque actuel", f"{risk_icons.get(curr_risk, '⚪')} {curr_risk}")
        ev_icons = {"BAISSE": "📉", "STABLE": "➡️", "HAUSSE": "📈"}
        ev_col3.metric("Évolution", f"{ev_icons.get(evolution, '?')} {evolution}")
        w_icons = {"LEVE": "✅", "CONFIRME": "🔴", "EN_SURVEILLANCE": "🔍"}
        ev_col4.metric("Warning", f"{w_icons.get(warning, '?')} {warning}")

        if warning == "LEVE":
            st.success(f"✅ **Risque levé** — {output2['sentinelle_message']}")
        elif warning == "CONFIRME":
            st.error(f"🔴 **Risque confirmé** — {output2['sentinelle_message']}")
        else:
            st.warning(f"🔍 **En surveillance** — {output2['sentinelle_message']}")

        # ── ETA actualisée des pièces ─────────────────────────
        st.markdown("---")
        st.markdown("#### 📦 Suivi des pièces")

        tracking = output2.get("parts_tracking", [])
        if tracking:
            track_rows = []
            for pt in tracking:
                status_icons = {"REÇU": "✅", "EN_ATTENTE": "⏳", "MANQUANT": "❌"}
                track_rows.append({
                    "Composant": pt["itemCode"],
                    "Statut initial": pt["initial_status"],
                    "Statut actuel": f"{status_icons.get(pt['current_status'], '?')} {pt['current_status']}",
                    "Fournisseur": pt.get("supplier", "—"),
                    "ETA initiale": pt.get("eta_initial", "—"),
                    "ETA actualisée": pt.get("eta_updated", "—"),
                    "Qté reçue": pt.get("qty_received", 0),
                })
            st.dataframe(pd.DataFrame(track_rows), use_container_width=True, hide_index=True)
        else:
            st.info("Pas de suivi pièces disponible.")

        # ── Impact mis à jour ─────────────────────────────────
        st.markdown("---")
        st.markdown("#### 📅 Impact actualisé")

        imp_col1, imp_col2, imp_col3 = st.columns(3)
        imp_col1.metric("Date de fin estimée", output2.get("updated_eta_end", "—"))
        imp_col2.metric("Retard actualisé", f"+{output2.get('updated_delay_days', 0)} j")
        imp_col3.metric("Priorité reprise", f"{output2.get('resume_priority', '?')}/5")

        if output2.get("resume_priority_reasoning"):
            st.caption(f"📋 {output2['resume_priority_reasoning']}")

        # ── Section impacts comparés ──────────────────────────
        st.markdown("---")
        st.markdown("#### 🔀 Comparaison : avec vs sans recommandation IA")

        maestro_delay = m_ref.get("estimated_delay_days", 0)
        sentinelle_delay = output2.get("updated_delay_days", 0)
        maestro_action = m_ref.get("recommended_action", "?")

        comp_data = {
            "Scénario": [
                "Si on suit la recommandation Maestro",
                "Si on reste sur le plan initial (sans IA)",
            ],
            "Retard estimé": [
                f"+{sentinelle_delay} j" if sentinelle_delay > 0 else "Aucun",
                f"+{maestro_delay} j" if maestro_delay > 0 else "Risque non quantifié",
            ],
            "Risque de blocage": [
                f"{output2.get('current_risk_level', '?')}",
                f"{m_ref.get('probabilite_blocage_pct', '?')}%",
            ],
        }
        st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)

        # ── Recommandations fournisseurs ──────────────────────
        if output2.get("supplier_recommendations"):
            st.markdown("---")
            st.markdown("#### 📦 Recommandations fournisseur")
            st.dataframe(
                pd.DataFrame(output2["supplier_recommendations"]),
                use_container_width=True, hide_index=True,
            )

        # ── Plan B — Reprise / blocage (worst case) ──────────
        st.markdown("---")
        if output2.get("plan_b_needed"):
            st.markdown("#### 🚨 Plan B — Reprise / blocage (worst case)")
            st.caption(
                "*Seulement dans les cas critiques où, malgré l'anticipation, "
                "la production a dû être stoppée.*"
            )

            prop = output2.get("rescheduling_proposal")
            if prop:
                st.error(
                    f"🔄 **Reprogrammation proposée** : {prop['label']}\n\n"
                    f"- Lancement : {prop['launch_date']}\n"
                    f"- Fin estimée : {prop['estimated_completion']}\n"
                    f"- Retard client : +{prop['delay_client_days']} jours\n"
                    f"- Pénalités : {prop['penalty_eur']:,.0f} €"
                )

            if order2["status"] == "RisqueLeve":
                st.warning(
                    "⚠️ Le bouton « Reprendre la production » est disponible dans le Cockpit (Page 1)."
                )
        else:
            st.success("✅ Pas de Plan B nécessaire — situation sous contrôle.")

        # ── Prompt et JSON ───────────────────────────────────
        _s_prompt = build_live_context_sentinelle(
            selected_of2, order2.get("priority", "?"), order2.get("dueDate", "?")[:10],
            m_ref, order2["stock"],
            output2.get("still_missing_components", []), output2.get("resolved_components", []),
        )
        with st.expander("📝 Prompt envoyé à Sentinelle"):
            st.code(SENTINELLE_SYSTEM_PROMPT, language="markdown")
            st.code(_s_prompt, language="markdown")

        with st.expander("🔧 JSON technique"):
            st.json(output2)
