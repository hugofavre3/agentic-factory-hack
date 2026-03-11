"""Page 2 — Dans la tête de l'IA (Détail Agents).

Les Assistants IA : décisions expliquées et argumentées.
"""

import streamlit as st
import pandas as pd
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data import (
    build_seed_orders, ROUTING,
    _check_availability, _find_cutoff, _find_last_doable,
    build_live_context_agent1, build_live_context_agent2,
    AGENT1_SYSTEM_PROMPT, AGENT2_SYSTEM_PROMPT,
)

st.set_page_config(page_title="Dans la tête de l'IA", page_icon="🧠", layout="wide")

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

# =============================================================================
# Titre + accroche
# =============================================================================

st.title("🧠 Les Assistants IA : Décisions expliquées et argumentées")

st.markdown(
    "*L'IA n'est pas une boîte noire. Sur cette page, vous pouvez voir comment "
    "Agent 1 et Agent 2 analysent la situation et pourquoi ils font leurs recommandations. "
    "Ils croisent le stock, la gamme, l'historique et les contraintes clients pour vous aider à décider.*"
)

st.divider()

# =============================================================================
# Onglets
# =============================================================================

tab1, tab2 = st.tabs([
    "🚀 Agent 1 — Stratégie de lancement",
    "🔍 Agent 2 — Reprise et approvisionnement",
])

# =============================================================================
# Onglet Agent 1
# =============================================================================

with tab1:
    st.markdown("### Comment lancer cet OF ?")
    st.caption(
        "L'Agent 1 a croisé les nomenclatures (BOM) et le stock. "
        "Il a évalué le risque en fonction de nos historiques de pannes ou retards."
    )

    a1_outputs = st.session_state["agent1_outputs"]

    if not a1_outputs:
        st.info("Aucun output Agent 1. Allez dans le **Cockpit Jour J** et lancez Agent 1 sur un OF.")
    else:
        # Filtrer l'OF custom pour le selectbox
        a1_keys = [k for k in a1_outputs if k in orders]
        selected_of = st.selectbox(
            "Sélectionner un OF :",
            options=a1_keys,
            format_func=lambda x: f"{orders[x]['orderNumber']} — {orders[x]['scenario_label']}",
            key="a1_select",
        )

        output = a1_outputs[selected_of]
        order = orders[selected_of]

        # ── Résumé décision ──────────────────────────────────
        st.markdown("---")
        op_dec = output.get("operator_decision")
        if op_dec:
            st.markdown("#### Décision validée par l'opérateur")
        else:
            st.markdown("#### Recommandation de l'IA (en attente de validation)")

        c1, c2, c3 = st.columns(3)

        decision = output.get("operator_decision") or output.get("recommended_decision", "?")
        risk = output["risk_level"]
        score = output["global_risk_score"]

        decision_labels = {
            "FULL_RELEASE": ("🟢 Lancement complet", "Tous les composants sont disponibles."),
            "PARTIAL_RELEASE": ("🟠 Lancement partiel", "On peut démarrer mais il manque des pièces en aval."),
            "DELAYED_RELEASE": ("🔴 Report recommandé", "Trop de composants critiques manquants."),
        }
        label, desc = decision_labels.get(decision, ("?", ""))

        c1.metric("Décision", label.split(" ", 1)[1])
        c2.metric("Score de risque", f"{score}/100")
        c3.metric("Créneau recommandé", output.get("recommended_start_slot") or "Aucun")

        # Couleur
        if decision == "FULL_RELEASE":
            st.success(f"{label} — {desc}")
        elif decision == "PARTIAL_RELEASE":
            st.warning(f"{label} — {desc}")
        else:
            st.error(f"{label} — {desc}")

        st.markdown(f"**Consigne atelier** : {output.get('instruction', '⏳ En attente de décision opérateur')}")

        # ── Explication IA ──────────────────────────────────────
        if output.get("ai_reasoning"):
            st.markdown("---")
            st.markdown("#### 💬 Explication de l'IA")
            st.markdown(
                "*On peut lancer en partiel, il manque seulement les freins, "
                "historiquement délai moyen 2 jours, peu d'impact client attendu.*"
                if decision == "PARTIAL_RELEASE" else ""
            )
            st.write(output["ai_reasoning"])

        # ── Pourquoi ce choix ? ──────────────────────────────────
        st.markdown("---")
        st.markdown("#### 📋 Pourquoi ce choix ?")

        # Stock actuel
        st.markdown("**Stock actuel**")
        stock_rows = []
        for comp in order["components"]:
            needed = comp["qtyPerUnit"] * order["quantity"]
            avail = order["stock"].get(comp["itemCode"], 0)
            crit = "🔴 Critique" if comp.get("isCritical") else ""
            stock_rows.append({
                "Composant": comp["itemCode"],
                "Besoin": needed,
                "Disponible": avail,
                "État": "✅" if avail >= needed else "❌",
                "Critique": crit,
            })
        st.dataframe(pd.DataFrame(stock_rows), use_container_width=True, hide_index=True)

        # Pièces manquantes
        if output.get("missing_components"):
            st.markdown("**Pièces manquantes**")
            mc_df = pd.DataFrame(output["missing_components"])
            st.dataframe(mc_df, use_container_width=True, hide_index=True)

        # Contrainte atelier (calendrier)
        if output.get("recommended_start_slot"):
            st.markdown(f"**Contrainte calendrier** : créneau recommandé `{output['recommended_start_slot']}`")

        if output.get("estimated_production_days"):
            st.markdown(f"**Durée estimée** : {output['estimated_production_days']} jours")

        # SLA
        if output.get("sla_impact"):
            st.markdown(f"**Impact SLA** : {output['sla_impact']}")

        # Facteurs de risque
        if output.get("risk_factors"):
            st.markdown("**Facteurs de risque**")
            st.dataframe(pd.DataFrame(output["risk_factors"]), use_container_width=True, hide_index=True)

        # Opération de coupure
        if output.get("cutoff_operation"):
            st.markdown("**Opération de coupure (point d'arrêt)**")
            co = output["cutoff_operation"]
            st.markdown(f"- Arrêt à : **{co['operationId']}** (séq. {co['sequence']}) — {co['description']}")

        # ── Gamme ────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("#### 🔧 Gamme de fabrication")
        missing_codes = {mc["itemCode"] for mc in output.get("missing_components", [])}
        routing_rows = []
        for op in ROUTING:
            blocked = set(op.get("requiredComponents", [])) & missing_codes
            routing_rows.append({
                "Séq.": op["sequence"],
                "Opération": op["operationId"],
                "Description": op["description"],
                "Composants": ", ".join(op.get("requiredComponents", [])),
                "État": "🔴 Bloqué" if blocked else "🟢 OK",
            })
        st.dataframe(pd.DataFrame(routing_rows), use_container_width=True, hide_index=True)

        # ── Prompt IA ──────────────────────────────────────────
        _missing = _check_availability(order["components"], order["quantity"], order["stock"])
        _cutoff = _find_cutoff(ROUTING, _missing)
        _last = _find_last_doable(ROUTING, _cutoff)
        _mvp = "FULL_RELEASE" if not _missing else "PARTIAL_RELEASE"
        _prompt = build_live_context_agent1(order, order["stock"], _missing, _mvp, _cutoff, _last)

        with st.expander("📝 Prompt envoyé à l'Agent 1"):
            st.markdown("**System prompt** :")
            st.code(AGENT1_SYSTEM_PROMPT, language="markdown")
            st.markdown(f"**Contexte utilisateur** ({len(_prompt)} car.) :")
            st.code(_prompt, language="markdown")

        with st.expander("🔧 Détail technique (JSON complet)"):
            st.json(output)


# =============================================================================
# Onglet Agent 2
# =============================================================================

with tab2:
    st.markdown("### Quand et comment reprendre la production ?")
    st.caption(
        "L'Agent 2 surveille la 'watchlist'. S'il manque des pièces, "
        "il anticipe les livraisons. Si elles sont là, il vous donne le feu vert pour reprendre."
    )

    a2_outputs = st.session_state["agent2_outputs"]

    if not a2_outputs:
        st.info("Aucun output Agent 2. Allez dans le **Cockpit Jour J** et lancez Agent 2.")
    else:
        a2_keys = [k for k in a2_outputs if k in orders]
        selected_of2 = st.selectbox(
            "Sélectionner un OF :",
            options=a2_keys,
            format_func=lambda x: f"{orders[x]['orderNumber']} — {orders[x]['scenario_label']}",
            key="a2_select",
        )

        output2 = a2_outputs[selected_of2]
        order2 = orders[selected_of2]
        a1_ref = st.session_state["agent1_outputs"].get(selected_of2, {})

        # ── État des pièces ──────────────────────────────────────
        st.markdown("---")
        st.markdown("#### 📦 État des pièces")

        col_p1, col_p2 = st.columns(2)

        with col_p1:
            st.markdown("**Composants manquants initialement** (Agent 1)")
            missing_from_a1 = a1_ref.get("missing_components", [])
            if missing_from_a1:
                st.dataframe(pd.DataFrame(missing_from_a1), use_container_width=True, hide_index=True)
            else:
                st.write("Aucun composant manquant.")

        with col_p2:
            if output2.get("resolved_components"):
                st.markdown("**✅ Revenus en stock**")
                st.dataframe(pd.DataFrame(output2["resolved_components"]), use_container_width=True, hide_index=True)

            if output2.get("still_missing_components"):
                st.markdown("**❌ Encore manquants**")
                for sm in output2["still_missing_components"]:
                    crit = " ⚠️ CRITIQUE" if sm.get("isCritical") else ""
                    st.markdown(f"- **{sm['itemCode']}**{crit} — besoin {sm['qtyNeeded']}, dispo {sm['qtyAvailableNow']}, manque **{sm['qtyStillShort']}**")

        # ETA
        if output2.get("overall_eta_days") is not None:
            st.markdown(f"**ETA estimée** : {output2['overall_eta_days']} jours")

        # ── Décision de reprise ──────────────────────────────────
        st.markdown("---")
        st.markdown("#### 🚦 Feu vert atelier : Instructions de reprise")

        c_r1, c_r2, c_r3 = st.columns(3)
        c_r1.metric("Statut", output2["new_status"])
        c_r2.metric("Priorité reprise", f"{output2.get('resume_priority', '?')}/5")
        resume_op = output2.get("resume_from_operation", {})
        c_r3.metric("Reprendre à", resume_op.get("operationId", "—") if resume_op else "—")

        if output2["new_status"] == "ReadyToResume":
            st.success(f"✅ **Prêt à reprendre** — Reprendre à {resume_op.get('operationId', '?') if resume_op else '?'}")
        else:
            st.warning(f"⏳ **Encore en attente** — Priorité reprise : {output2.get('resume_priority', '?')}/5")

        st.markdown(f"**Consigne** : {output2['instruction']}")

        if output2.get("resume_priority_reasoning"):
            st.markdown(f"**Justification priorité** : {output2['resume_priority_reasoning']}")

        if output2.get("ai_notification"):
            st.info(f"📢 {output2['ai_notification']}")

        # ── Action achat / supply ────────────────────────────────
        if output2.get("supplier_recommendations"):
            st.markdown("---")
            st.markdown("#### 📦 Anticipation des pénuries (ETA et sourcing)")
            st.caption("Recommandations de commande fournisseur pour les pièces manquantes.")
            st.dataframe(pd.DataFrame(output2["supplier_recommendations"]), use_container_width=True, hide_index=True)

        if output2.get("risk_assessment"):
            st.markdown(f"**Évaluation du risque** : {output2['risk_assessment']}")

        # ── Prompt IA ──────────────────────────────────────────
        _a2_prompt = build_live_context_agent2(
            selected_of2, order2.get("priority", "?"), order2.get("dueDate", "?")[:10],
            a1_ref, order2["stock"],
            output2.get("still_missing_components", []), output2.get("resolved_components", []),
        )
        with st.expander("📝 Prompt envoyé à l'Agent 2"):
            st.markdown("**System prompt** :")
            st.code(AGENT2_SYSTEM_PROMPT, language="markdown")
            st.markdown(f"**Contexte utilisateur** ({len(_a2_prompt)} car.) :")
            st.code(_a2_prompt, language="markdown")

        with st.expander("🔧 Détail technique (JSON complet)"):
            st.json(output2)
