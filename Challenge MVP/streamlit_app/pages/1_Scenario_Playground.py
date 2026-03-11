"""Page 1 — Scenario Playground.

Tests live des 3 scénarios avec boutons Agent 1 / Orchestrateur / Agent 2.
"""

import streamlit as st
import pandas as pd
import sys, os

# Import data module from parent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data import run_agent1, run_orchestrator, run_agent2, build_seed_orders

st.set_page_config(page_title="Scenario Playground", page_icon="🎮", layout="wide")

# Init session state si navigation directe
if "orders" not in st.session_state:
    st.session_state["orders"] = build_seed_orders()
if "agent1_outputs" not in st.session_state:
    st.session_state["agent1_outputs"] = {}
if "agent2_outputs" not in st.session_state:
    st.session_state["agent2_outputs"] = {}
if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = []

orders = st.session_state["orders"]

st.title("🎮 Scenario Playground")

st.info(
    "💡 **Dans la vraie vie**, Agent 1 est déclenché manuellement ou en batch sur un OF. "
    "Ici, chaque clic de bouton simule un trigger manuel."
)

st.divider()

# =============================================================================
# Sélection de scénario
# =============================================================================

left, right = st.columns([1, 2])

with left:
    st.subheader("Sélection du scénario")

    scenario_labels = {of["of_id"]: of["scenario_label"] for of in orders.values()}
    selected_of_id = st.radio(
        "Choisir un OF :",
        options=list(scenario_labels.keys()),
        format_func=lambda x: scenario_labels[x],
    )

    selected_order = orders[selected_of_id]

    st.markdown("---")
    st.markdown("**Résumé de l'OF sélectionné**")
    st.markdown(f"- **OF** : `{selected_order['orderNumber']}`")
    st.markdown(f"- **Produit** : `{selected_order['productCode']}`")
    st.markdown(f"- **Quantité** : `{selected_order['quantity']}`")
    st.markdown(f"- **Priorité** : `{selected_order['priority']}`")
    st.markdown(f"- **Échéance** : `{selected_order['dueDate'][:10]}`")
    st.markdown(f"- **Statut** : `{selected_order['status']}`")

    st.markdown("---")
    st.markdown("**Stock disponible**")
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
    # =========================================================================
    # Bouton Agent 1
    # =========================================================================
    st.subheader("① Agent 1 — Planification OF")

    if st.button("🚀 Lancer Agent 1 sur cet OF", key="btn_agent1", type="primary"):
        output = run_agent1(selected_of_id, orders)
        st.session_state["agent1_outputs"][selected_of_id] = output

        # Décision métier lisible
        decision = output["decision"]
        risk = output["risk_level"]
        score = output["global_risk_score"]

        if decision == "FULL_RELEASE":
            st.success(f"✅ **{decision}** — Risque {risk} ({score}/100)")
        elif decision == "PARTIAL_RELEASE":
            st.warning(f"⚠️ **{decision}** — Risque {risk} ({score}/100)")
        else:
            st.error(f"🛑 **{decision}** — Risque {risk} ({score}/100)")

        st.markdown(f"**Statut OF** : `{output['new_status']}`")
        st.markdown(f"**Créneau recommandé** : `{output.get('recommended_start_slot', 'Aucun')}`")
        st.markdown(f"**Consigne** : {output['instruction']}")

        if output.get("ai_reasoning"):
            with st.expander("💬 Explication IA détaillée"):
                st.write(output["ai_reasoning"])

        if output.get("risk_factors"):
            with st.expander("📊 Facteurs de risque"):
                rf_df = pd.DataFrame(output["risk_factors"])
                st.dataframe(rf_df, use_container_width=True, hide_index=True)

        with st.expander("📄 Output JSON Agent 1 complet"):
            st.json(output)

    # Afficher le dernier output si existant
    elif selected_of_id in st.session_state["agent1_outputs"]:
        output = st.session_state["agent1_outputs"][selected_of_id]
        decision = output["decision"]
        risk = output["risk_level"]
        score = output["global_risk_score"]

        if decision == "FULL_RELEASE":
            st.success(f"✅ **{decision}** — Risque {risk} ({score}/100)")
        elif decision == "PARTIAL_RELEASE":
            st.warning(f"⚠️ **{decision}** — Risque {risk} ({score}/100)")
        else:
            st.error(f"🛑 **{decision}** — Risque {risk} ({score}/100)")

        st.markdown(f"**Statut OF** : `{output['new_status']}`")
        st.markdown(f"**Consigne** : {output['instruction']}")

        with st.expander("📄 Output JSON Agent 1 complet"):
            st.json(output)

    st.divider()

    # =========================================================================
    # Bouton Orchestrateur
    # =========================================================================
    st.subheader("② Orchestrateur — Watchlist")

    if st.button("🔗 Mettre à jour la watchlist (Orchestrateur)", key="btn_orch"):
        a1_outputs = st.session_state["agent1_outputs"]
        if not a1_outputs:
            st.warning("Aucun output Agent 1 disponible. Lancez d'abord Agent 1 sur au moins un OF.")
        else:
            watchlist = run_orchestrator(a1_outputs)
            st.session_state["watchlist"] = watchlist

            if watchlist:
                st.success(f"✅ Watchlist générée — {len(watchlist)} OF à surveiller")
                wl_df = pd.DataFrame(watchlist)
                st.dataframe(wl_df, use_container_width=True, hide_index=True)
            else:
                st.info("Aucun OF en PartiallyReleased ou Delayed — rien à surveiller.")

    elif st.session_state["watchlist"]:
        st.markdown(f"**Watchlist actuelle** : {len(st.session_state['watchlist'])} OF")
        wl_df = pd.DataFrame(st.session_state["watchlist"])
        st.dataframe(wl_df, use_container_width=True, hide_index=True)

    st.divider()

    # =========================================================================
    # Bouton Agent 2
    # =========================================================================
    st.subheader("③ Agent 2 — Surveillance stock & reprise")

    if st.button("🔍 Lancer Agent 2 sur la watchlist", key="btn_agent2", type="primary"):
        watchlist = st.session_state["watchlist"]
        if not watchlist:
            st.warning("Watchlist vide. Lancez d'abord l'orchestrateur.")
        else:
            results = run_agent2(orders, st.session_state["agent1_outputs"], watchlist)

            for res in results:
                st.session_state["agent2_outputs"][res["of_id"]] = res

            # Afficher les résultats
            for res in results:
                of_id = res["of_id"]
                new_status = res["new_status"]

                if new_status == "ReadyToResume":
                    st.success(f"✅ **{of_id}** → **ReadyToResume** — Priorité {res.get('resume_priority', '?')}/5")
                else:
                    st.warning(f"⏳ **{of_id}** → **{new_status}** — Priorité {res.get('resume_priority', '?')}/5")

                st.markdown(f"**Consigne** : {res['instruction']}")

                if res.get("ai_notification"):
                    st.info(f"📢 {res['ai_notification']}")

                if res.get("supplier_recommendations"):
                    with st.expander(f"📦 Recommandations fournisseurs — {of_id}"):
                        sup_df = pd.DataFrame(res["supplier_recommendations"])
                        st.dataframe(sup_df, use_container_width=True, hide_index=True)

                with st.expander(f"📄 Output JSON Agent 2 — {of_id}"):
                    st.json(res)

            # Mettre à jour la watchlist (retirer les ReadyToResume)
            st.session_state["watchlist"] = [
                w for w in watchlist
                if orders[w["of_id"]]["status"] not in ("ReadyToResume", "Released")
            ]
