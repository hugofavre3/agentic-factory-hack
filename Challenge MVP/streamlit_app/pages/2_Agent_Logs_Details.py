"""Page 2 — Agent Logs & Details.

Vue détaillée et pédagogique des agents : inputs, outputs, timeline.
"""

import streamlit as st
import pandas as pd
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data import build_seed_orders, ROUTING

st.set_page_config(page_title="Agent Logs & Details", page_icon="🔎", layout="wide")

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

st.title("🔎 Agent Logs & Details")

tab1, tab2 = st.tabs(["Agent 1 — Planification OF", "Agent 2 — Surveillance stock & reprise"])

# =============================================================================
# Onglet Agent 1
# =============================================================================

with tab1:
    a1_outputs = st.session_state["agent1_outputs"]

    if not a1_outputs:
        st.info("Aucun output Agent 1 disponible. Allez dans **Scenario Playground** et lancez Agent 1.")
    else:
        selected_of = st.selectbox(
            "Sélectionner un OF :",
            options=list(a1_outputs.keys()),
            format_func=lambda x: f"{x} — {orders[x]['scenario_label']}",
            key="a1_select",
        )

        output = a1_outputs[selected_of]
        order = orders[selected_of]

        # --- Input simulé ---
        st.subheader("📥 Input Agent 1")
        col_in1, col_in2 = st.columns(2)

        with col_in1:
            st.markdown("**OF**")
            st.json({
                "id": order["of_id"],
                "orderNumber": order["orderNumber"],
                "productCode": order["productCode"],
                "quantity": order["quantity"],
                "priority": order["priority"],
                "dueDate": order["dueDate"],
            })

            st.markdown("**BOM (composants)**")
            bom_df = pd.DataFrame(order["components"])
            bom_df["Besoin total"] = bom_df["qtyPerUnit"] * order["quantity"]
            st.dataframe(bom_df, use_container_width=True, hide_index=True)

        with col_in2:
            st.markdown("**Gamme (opérations)**")
            routing_df = pd.DataFrame(ROUTING)
            st.dataframe(routing_df[["operationId", "sequence", "description", "requiredComponents"]],
                         use_container_width=True, hide_index=True)

            st.markdown("**Stock snapshot**")
            stock_df = pd.DataFrame([
                {"itemCode": k, "qtyAvailable": v}
                for k, v in order["stock"].items()
            ])
            st.dataframe(stock_df, use_container_width=True, hide_index=True)

        st.divider()

        # --- Output Agent 1 ---
        st.subheader("📤 Output Agent 1")

        # Timeline visuelle
        st.markdown("**Timeline de décision**")
        col_t1, col_t2, col_t3 = st.columns(3)
        col_t1.metric("Statut avant", output["previous_status"])
        col_t2.metric("Décision", output["decision"])
        col_t3.metric("Statut après", output["new_status"])

        col_r1, col_r2, col_r3 = st.columns(3)
        col_r1.metric("Score risque", f"{output['global_risk_score']}/100")
        col_r2.metric("Niveau risque", output["risk_level"])
        col_r3.metric("Créneau", output.get("recommended_start_slot") or "Aucun")

        st.markdown(f"**Consigne atelier** : {output['instruction']}")

        if output.get("ai_reasoning"):
            with st.expander("💬 Explication IA"):
                st.write(output["ai_reasoning"])

        if output.get("risk_factors"):
            with st.expander("📊 Facteurs de risque"):
                rf_df = pd.DataFrame(output["risk_factors"])
                st.dataframe(rf_df, use_container_width=True, hide_index=True)

        if output.get("missing_components"):
            with st.expander("❌ Composants manquants"):
                mc_df = pd.DataFrame(output["missing_components"])
                st.dataframe(mc_df, use_container_width=True, hide_index=True)

        if output.get("cutoff_operation"):
            with st.expander("✂️ Opération de coupure"):
                st.json(output["cutoff_operation"])

        with st.expander("📄 JSON complet Agent 1"):
            st.json(output)


# =============================================================================
# Onglet Agent 2
# =============================================================================

with tab2:
    a2_outputs = st.session_state["agent2_outputs"]

    if not a2_outputs:
        st.info("Aucun output Agent 2 disponible. Allez dans **Scenario Playground** et lancez Agent 2.")
    else:
        selected_of2 = st.selectbox(
            "Sélectionner un OF :",
            options=list(a2_outputs.keys()),
            format_func=lambda x: f"{x} — {orders[x]['scenario_label']}",
            key="a2_select",
        )

        output2 = a2_outputs[selected_of2]
        order2 = orders[selected_of2]

        # --- État watchlist ---
        st.subheader("📥 Input Agent 2")

        col_w1, col_w2 = st.columns(2)
        with col_w1:
            st.markdown("**Entrée watchlist**")
            # Trouver l'entrée correspondante
            a1_out = st.session_state["agent1_outputs"].get(selected_of2, {})
            st.json({
                "of_id": selected_of2,
                "status_avant_agent2": output2["previous_status"],
                "decision_agent1": a1_out.get("decision", "?"),
                "risk_level_agent1": a1_out.get("risk_level", "?"),
            })

        with col_w2:
            st.markdown("**Composants manquants (depuis Agent 1)**")
            missing_from_a1 = a1_out.get("missing_components", [])
            if missing_from_a1:
                mc_df = pd.DataFrame(missing_from_a1)
                st.dataframe(mc_df, use_container_width=True, hide_index=True)
            else:
                st.write("Aucun composant manquant.")

        st.divider()

        # --- Output Agent 2 ---
        st.subheader("📤 Output Agent 2")

        col_o1, col_o2, col_o3 = st.columns(3)
        col_o1.metric("Statut avant", output2["previous_status"])
        col_o2.metric("Statut après", output2["new_status"])
        col_o3.metric("Priorité reprise", f"{output2.get('resume_priority', '?')}/5")

        if output2.get("overall_eta_days") is not None:
            st.metric("ETA reprise estimée", f"{output2['overall_eta_days']} jours")

        st.markdown(f"**Consigne** : {output2['instruction']}")

        if output2.get("ai_notification"):
            st.info(f"📢 {output2['ai_notification']}")

        if output2.get("resolved_components"):
            with st.expander("✅ Composants résolus"):
                res_df = pd.DataFrame(output2["resolved_components"])
                st.dataframe(res_df, use_container_width=True, hide_index=True)

        if output2.get("still_missing_components"):
            with st.expander("❌ Composants encore manquants"):
                sm_df = pd.DataFrame(output2["still_missing_components"])
                st.dataframe(sm_df, use_container_width=True, hide_index=True)

        if output2.get("supplier_recommendations"):
            with st.expander("📦 Recommandations fournisseurs"):
                sup_df = pd.DataFrame(output2["supplier_recommendations"])
                st.dataframe(sup_df, use_container_width=True, hide_index=True)

        if output2.get("risk_assessment"):
            with st.expander("⚠️ Évaluation risque"):
                st.write(output2["risk_assessment"])

        with st.expander("📄 JSON complet Agent 2"):
            st.json(output2)
