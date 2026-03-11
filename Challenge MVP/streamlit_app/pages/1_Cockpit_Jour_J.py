"""Page 1 — Cockpit Jour J (Supervision Terrain).

Vue opérationnelle : KPIs, tableau des OF, simulation agents, focus OF.
"""

import streamlit as st
import pandas as pd
import sys, os
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data import (
    run_agent1, run_orchestrator, run_agent2, build_seed_orders,
    BOM_FULL, DEFAULT_STOCK, ROUTING,
    _check_availability, _find_cutoff, _find_last_doable,
    build_live_context_agent1, build_live_context_agent2,
    AGENT1_SYSTEM_PROMPT, AGENT2_SYSTEM_PROMPT,
    call_llm, SUPPLIERS_DATA,
    get_stock_updates_preview, resume_of,
)

st.set_page_config(page_title="Cockpit Jour J", page_icon="📋", layout="wide")

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

st.title("📋 Supervision Atelier : OF du jour et alertes en temps réel")

st.markdown(
    "*Dans la vraie vie, ce cockpit s'actualise en continu (ou par batch). "
    "Il vous permet de voir en un coup d'œil quels Ordres de Fabrication peuvent être lancés, "
    "lesquels sont bloqués, et lesquels sont prêts à repartir.*"
)

# =============================================================================
# Bandeau KPIs terrain
# =============================================================================

st.divider()

total_of = len(sim_orders)
k1, k2, k3, k4 = st.columns(4)

status_counts = {}
for s in ["Created", "Released", "PartiallyReleased", "Delayed", "ReadyToResume"]:
    status_counts[s] = sum(1 for o in sim_orders.values() if o["status"] == s)

critical_count = sum(
    1 for of_id, o in sim_orders.items()
    if st.session_state["agent1_outputs"].get(of_id, {}).get("risk_level") == "HIGH"
    or st.session_state["agent1_outputs"].get(of_id, {}).get("global_risk_score", 0) > 60
)

k1.metric("📐 Non traités", status_counts["Created"], help="OF pas encore analysés par Agent 1")
k2.metric("🟠 Attente pièces", status_counts["PartiallyReleased"] + status_counts["Delayed"], help="Partiels + reportés")
k3.metric("✅ Prêts / Lancés", status_counts["ReadyToResume"] + status_counts["Released"], help="Prêts à reprendre + lancés complets")
k4.metric("📦 Total OF", total_of)

if critical_count:
    st.caption(f"⚠️ Dont **{critical_count}** OF critique(s) (score risque > 60)")

# =============================================================================
# Tableau "OF du jour"
# =============================================================================

st.divider()
st.subheader("📊 Statut en direct — OF du jour")

rows = []
for of_id, order in sim_orders.items():
    a1 = st.session_state["agent1_outputs"].get(of_id, {})
    a2 = st.session_state["agent2_outputs"].get(of_id, {})

    risk_level = a1.get("risk_level", "—")
    score = a1.get("global_risk_score", "—")

    missing = a1.get("missing_components", [])
    if missing:
        manquants = ", ".join(mc["itemCode"] for mc in missing[:3])
        if len(missing) > 3:
            manquants += f" +{len(missing)-3}"
    else:
        manquants = "Aucun" if a1 else "—"

    status = order["status"]
    status_labels = {
        "Released": "🟢 Lancé",
        "PartiallyReleased": "🟠 Partiel",
        "Delayed": "🔴 Différé",
        "ReadyToResume": "✅ Prêt reprise",
    }
    status_label = status_labels.get(status, "🔵 En attente")

    risk_icon = {"HIGH": "🔴", "MEDIUM": "🟠", "LOW": "🟢"}.get(risk_level, "⚪")

    rows.append({
        "OF": order["orderNumber"],
        "Produit": order["productCode"],
        "Statut": status_label,
        "Risque": f"{risk_icon} {risk_level}",
        "Score": score,
        "Manquants": manquants,
        "ETA reprise": f"{a2.get('overall_eta_days', '—')}j" if a2.get('overall_eta_days') else "—",
        "Priorité": order["priority"],
        "Dernier agent": order.get("last_agent", "—"),
    })

if rows:
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.info("Aucun OF chargé.")

# =============================================================================
# Actions de la journée — Simulation 3 scénarios
# =============================================================================

st.divider()
st.subheader("⚡ Simuler la journée — 3 situations courantes")

st.caption(
    "💡 **Dans la vraie vie** : Agent 1 tourne en batch matinal ou au fil de l'eau. "
    "L'orchestrateur scanne en continu. Agent 2 vérifie toutes les 10 minutes et alerte dès qu'un OF peut reprendre."
)

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
    st.markdown(f"- Échéance : **{selected_order['dueDate'][:10]}**")
    st.markdown(f"- Statut : **{selected_order['status']}**")

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

    # ─── Agent 1 ────────────────────────────────────────────────
    st.markdown("#### 🚀 Lancer l'analyse de lancement (Agent 1)")
    st.caption("*Simule l'analyse matinale : lancer en complet, en partiel, ou reporter ?*")

    if st.button("Lancer Agent 1 sur cet OF", key="btn_agent1", type="primary"):
        output = run_agent1(selected_of_id, orders)
        st.session_state["agent1_outputs"][selected_of_id] = output

        decision = output["decision"]
        risk = output["risk_level"]
        score = output["global_risk_score"]

        if decision == "FULL_RELEASE":
            st.success(f"✅ **Lancement complet** — Risque {risk} ({score}/100)")
        elif decision == "PARTIAL_RELEASE":
            st.warning(f"⚠️ **Lancement partiel** — Risque {risk} ({score}/100)")
        else:
            st.error(f"🛑 **Report recommandé** — Risque {risk} ({score}/100)")

        st.markdown(f"**Consigne atelier** : {output['instruction']}")

        if output.get("ai_reasoning"):
            with st.expander("💬 Explication de l'IA"):
                st.write(output["ai_reasoning"])

        if output.get("risk_factors"):
            with st.expander("📊 Facteurs de risque"):
                st.dataframe(pd.DataFrame(output["risk_factors"]), use_container_width=True, hide_index=True)

        _a1_missing = _check_availability(selected_order["components"], selected_order["quantity"], selected_order["stock"])
        _a1_cutoff = _find_cutoff(ROUTING, _a1_missing)
        _a1_last = _find_last_doable(ROUTING, _a1_cutoff)
        _a1_mvp = "FULL_RELEASE" if not _a1_missing else "PARTIAL_RELEASE"
        _a1_prompt = build_live_context_agent1(selected_order, selected_order["stock"], _a1_missing, _a1_mvp, _a1_cutoff, _a1_last)
        with st.expander("📝 Voir le prompt envoyé à l'Agent 1"):
            st.code(AGENT1_SYSTEM_PROMPT, language="markdown")
            st.code(_a1_prompt, language="markdown")

        with st.expander("🔧 Détail technique (JSON)"):
            st.json(output)

    elif selected_of_id in st.session_state["agent1_outputs"]:
        output = st.session_state["agent1_outputs"][selected_of_id]
        decision = output["decision"]
        risk = output["risk_level"]
        score = output["global_risk_score"]

        if decision == "FULL_RELEASE":
            st.success(f"✅ **Lancement complet** — Risque {risk} ({score}/100)")
        elif decision == "PARTIAL_RELEASE":
            st.warning(f"⚠️ **Lancement partiel** — Risque {risk} ({score}/100)")
        else:
            st.error(f"🛑 **Report recommandé** — Risque {risk} ({score}/100)")

        st.markdown(f"**Consigne atelier** : {output['instruction']}")

        _a1c_missing = _check_availability(selected_order["components"], selected_order["quantity"], selected_order["stock"])
        _a1c_cutoff = _find_cutoff(ROUTING, _a1c_missing)
        _a1c_last = _find_last_doable(ROUTING, _a1c_cutoff)
        _a1c_mvp = "FULL_RELEASE" if not _a1c_missing else "PARTIAL_RELEASE"
        _a1c_prompt = build_live_context_agent1(selected_order, selected_order["stock"], _a1c_missing, _a1c_mvp, _a1c_cutoff, _a1c_last)
        with st.expander("📝 Voir le prompt envoyé à l'Agent 1"):
            st.code(AGENT1_SYSTEM_PROMPT, language="markdown")
            st.code(_a1c_prompt, language="markdown")

        with st.expander("🔧 Détail technique (JSON)"):
            st.json(output)

    st.divider()

    # ─── Orchestrateur ──────────────────────────────────────────
    st.markdown("#### 🔗 Mettre à jour les OF en attente (Orchestrateur)")
    st.caption("*Quels OF doivent être surveillés par Agent 2 ?*")

    if st.button("Mettre à jour la watchlist", key="btn_orch"):
        a1_outputs = st.session_state["agent1_outputs"]
        if not a1_outputs:
            st.warning("Lancez d'abord Agent 1 sur au moins un OF.")
        else:
            watchlist = run_orchestrator(a1_outputs)
            st.session_state["watchlist"] = watchlist

            if watchlist:
                st.success(f"✅ {len(watchlist)} OF à surveiller")
                st.dataframe(pd.DataFrame(watchlist), use_container_width=True, hide_index=True)
            else:
                st.info("Aucun OF bloqué — rien à surveiller.")

    elif st.session_state["watchlist"]:
        st.markdown(f"**Watchlist** : {len(st.session_state['watchlist'])} OF en surveillance")
        st.dataframe(pd.DataFrame(st.session_state["watchlist"]), use_container_width=True, hide_index=True)

    st.divider()

    # ─── Réception stock (entre orchestrateur et Agent 2) ────────
    st.markdown("#### 📦 Réception stock simulée (fournisseurs)")
    st.caption(
        "*Entre l'analyse Agent 1 et la vérification Agent 2, le temps passe. "
        "Des livraisons fournisseur peuvent arriver et rendre les pièces disponibles.*"
    )

    watchlist = st.session_state["watchlist"]
    if watchlist:
        previews = get_stock_updates_preview(orders, watchlist)
        for prev in previews:
            of_label = prev["orderNumber"]
            if prev["has_arrivals"]:
                arr_rows = []
                for a in prev["arrivals"]:
                    if a["delta"] > 0:
                        arr_rows.append(a)
                if arr_rows:
                    st.success(f"📦 **{of_label}** — Livraisons reçues :")
                    st.dataframe(
                        pd.DataFrame(arr_rows)[["itemCode", "stock_avant", "stock_après", "delta", "type"]],
                        use_container_width=True, hide_index=True,
                    )
            else:
                st.info(f"📭 **{of_label}** — Aucune livraison reçue, stock inchangé.")
    else:
        st.caption("Lancez d'abord l'orchestrateur pour voir les mises à jour stock.")

    st.divider()

    # ─── Agent 2 ────────────────────────────────────────────────
    st.markdown("#### 🔍 Vérifier la dispo pièces et proposer la reprise (Agent 2)")
    st.caption("*L'Agent 2 compare le nouveau stock aux besoins restants.*")

    if st.button("Lancer Agent 2 sur la watchlist", key="btn_agent2", type="primary"):
        watchlist = st.session_state["watchlist"]
        if not watchlist:
            st.warning("Watchlist vide — lancez d'abord l'orchestrateur.")
        else:
            results = run_agent2(orders, st.session_state["agent1_outputs"], watchlist)
            for res in results:
                st.session_state["agent2_outputs"][res["of_id"]] = res

            for res in results:
                of_id = res["of_id"]
                new_status = res["new_status"]

                if new_status == "ReadyToResume":
                    st.success(f"✅ **{orders[of_id]['orderNumber']}** → **Prêt à reprendre** — Priorité {res.get('resume_priority', '?')}/5")
                else:
                    st.warning(f"⏳ **{orders[of_id]['orderNumber']}** → **Toujours en attente** — Priorité {res.get('resume_priority', '?')}/5")

                # Tableau avant/après stock pour les composants concernés
                if res.get("stock_arrivals"):
                    stock_rows = []
                    for sa in res["stock_arrivals"]:
                        needed = next(
                            (mc["qtyNeeded"] for mc in res.get("resolved_components", []) + res.get("still_missing_components", [])
                             if mc["itemCode"] == sa["itemCode"]),
                            "?"
                        )
                        stock_rows.append({
                            "Composant": sa["itemCode"],
                            "Stock (Agent 1)": sa["stock_agent1"],
                            "Stock (Agent 2)": sa["stock_agent2"],
                            "Δ Arrivée": f"+{sa['delta']}" if sa["delta"] > 0 else str(sa["delta"]) if sa["delta"] != 0 else "—",
                            "Besoin": needed,
                            "Résultat": "✅ Couvert" if sa["stock_agent2"] >= (needed if isinstance(needed, int) else 0) else "❌ Insuffisant",
                        })
                    with st.expander(f"📊 Évolution stock — {orders[of_id]['orderNumber']}"):
                        st.dataframe(pd.DataFrame(stock_rows), use_container_width=True, hide_index=True)

                st.markdown(f"**Consigne** : {res['instruction']}")

                if res.get("ai_notification"):
                    st.info(f"📢 {res['ai_notification']}")

                if res.get("supplier_recommendations"):
                    with st.expander(f"📦 Reco fournisseurs — {orders[of_id]['orderNumber']}"):
                        st.dataframe(pd.DataFrame(res["supplier_recommendations"]), use_container_width=True, hide_index=True)

                _a2_a1 = st.session_state["agent1_outputs"].get(of_id, {})
                _a2_order = orders[of_id]
                _a2_prompt = build_live_context_agent2(
                    of_id, _a2_order.get("priority", "?"), _a2_order.get("dueDate", "?")[:10],
                    _a2_a1, _a2_order["stock"],
                    res.get("still_missing_components", []), res.get("resolved_components", []),
                )
                with st.expander(f"📝 Prompt Agent 2 — {orders[of_id]['orderNumber']}"):
                    st.code(AGENT2_SYSTEM_PROMPT, language="markdown")
                    st.code(_a2_prompt, language="markdown")

                with st.expander(f"🔧 Détail technique (JSON) — {orders[of_id]['orderNumber']}"):
                    st.json(res)

            st.session_state["watchlist"] = [
                w for w in watchlist
                if orders[w["of_id"]]["status"] not in ("ReadyToResume", "Released")
            ]

    st.divider()

    # ─── Bouton Reprendre ───────────────────────────────────────
    st.markdown("#### ▶️ Reprendre la production")
    st.caption("*Validez la reprise d'un OF ReadyToResume → il passe en Lancé complet.*")

    ready_ofs = {of_id: o for of_id, o in sim_orders.items() if o["status"] == "ReadyToResume"}
    if ready_ofs:
        for of_id, order in ready_ofs.items():
            resume_op = st.session_state["agent2_outputs"].get(of_id, {}).get("resume_from_operation", {})
            op_label = resume_op.get("operationId", "?")
            col_btn, col_info = st.columns([1, 3])
            with col_btn:
                if st.button(f"▶️ Reprendre {order['orderNumber']}", key=f"btn_resume_{of_id}"):
                    resume_of(of_id, orders)
                    # Retirer de la watchlist
                    st.session_state["watchlist"] = [
                        w for w in st.session_state["watchlist"] if w["of_id"] != of_id
                    ]
                    st.success(f"✅ **{order['orderNumber']}** → **Lancé complet** (reprise à {op_label})")
                    st.rerun()
            with col_info:
                st.markdown(f"Reprendre à **{op_label}** — pièces disponibles")
    else:
        st.caption("Aucun OF prêt à reprendre pour le moment.")


# =============================================================================
# Focus OF — Timeline + messages agents
# =============================================================================

st.divider()
st.subheader("🔎 Focus sur un OF — Historique et consignes métier")
st.caption("*Au lieu de fouiller dans l'ERP, l'IA résume la situation et la consigne pour cet OF.*")

focus_options = {of_id: o["orderNumber"] for of_id, o in sim_orders.items()}
focus_of_id = st.selectbox(
    "Sélectionner un OF :",
    options=list(focus_options.keys()),
    format_func=lambda x: focus_options[x],
    key="focus_of",
)

focus_order = orders[focus_of_id]
a1_out = st.session_state["agent1_outputs"].get(focus_of_id, {})
a2_out = st.session_state["agent2_outputs"].get(focus_of_id, {})

# Timeline
st.markdown("**Progression de l'OF**")

if focus_order["status"] in ("Released", "ReadyToResume"):
    current_step = 4
elif a2_out:
    current_step = 3
elif focus_of_id in [w["of_id"] for w in st.session_state.get("watchlist", [])]:
    current_step = 2
elif a1_out:
    current_step = 1
else:
    current_step = 0

steps = ["Créé", "Décision Agent 1", "En watchlist", "Vérification Agent 2", "Prêt / Lancé"]
cols_tl = st.columns(5)
for i, (col, step) in enumerate(zip(cols_tl, steps)):
    if i < current_step:
        col.markdown(f"✅ **{step}**")
    elif i == current_step:
        col.markdown(f"🔵 **{step}**")
    else:
        col.markdown(f"⚪ {step}")

st.markdown("---")
st.markdown("**Derniers messages des agents**")

if a1_out:
    decision = a1_out["decision"]
    risk = a1_out["risk_level"]
    if decision == "FULL_RELEASE":
        a1_msg = "On lance en complet, risque faible. Tous les composants sont disponibles."
    elif decision == "PARTIAL_RELEASE":
        parts = ", ".join(mc["itemCode"] for mc in a1_out.get("missing_components", []))
        last_op = a1_out.get("cutoff_operation", {})
        before_op = last_op.get("description", "?") if last_op else "?"
        a1_msg = f"On lance en partiel — il manque {parts}. On produit jusqu'avant {before_op}, risque {risk.lower()}."
    else:
        parts = ", ".join(mc["itemCode"] for mc in a1_out.get("missing_components", []))
        a1_msg = f"Report recommandé — trop de composants critiques manquants ({parts}). Risque {risk.lower()}."

    st.info(f"🤖 **Agent 1** : {a1_msg}")

    if a1_out.get("ai_reasoning"):
        with st.expander("💬 Explication complète"):
            st.write(a1_out["ai_reasoning"])
else:
    st.caption("Agent 1 n'a pas encore analysé cet OF.")

if a2_out:
    new_status = a2_out["new_status"]
    if new_status == "ReadyToResume":
        resume_op = a2_out.get("resume_from_operation", {}).get("operationId", "?")
        resolved_parts = ", ".join(r["itemCode"] for r in a2_out.get("resolved_components", []))
        a2_msg = f"Pièces arrivées ({resolved_parts}), reprendre la production à {resume_op}."
    else:
        still = ", ".join(f"{sm['itemCode']} (manque {sm['qtyStillShort']})" for sm in a2_out.get("still_missing_components", []))
        eta = a2_out.get("overall_eta_days")
        a2_msg = f"Encore en attente — {still}."
        if eta:
            a2_msg += f" ETA estimée : {eta} jours."

    st.info(f"🤖 **Agent 2** : {a2_msg}")
    if a2_out.get("ai_notification"):
        st.success(f"📢 {a2_out['ai_notification']}")
else:
    st.caption("Agent 2 n'a pas encore vérifié cet OF.")


# =============================================================================
# Section Custom + IA temps réel
# =============================================================================

st.divider()
st.header("🔬 Scénario Custom — IA en temps réel")

st.markdown(
    "⚡ **Les 3 scénarios ci-dessus sont simulés** (outputs pré-remplis, zéro appel LLM). "
    "Ici, configurez vos propres inputs et appelez le **vrai LLM Azure AI**."
)

env_ok = bool(os.getenv("AZURE_AI_PROJECT_ENDPOINT") or os.getenv("AI_FOUNDRY_PROJECT_ENDPOINT"))
if not env_ok:
    st.warning(
        "⚠️ `AZURE_AI_PROJECT_ENDPOINT` non définie — mode déterministe uniquement.\n\n"
        "Pour activer l'IA : `export AZURE_AI_PROJECT_ENDPOINT=...` puis relancer Streamlit."
    )

custom_left, custom_right = st.columns([1, 2])

with custom_left:
    st.markdown("**Configurer l'OF**")

    c_qty = st.number_input("Quantité", min_value=1, max_value=20, value=4, key="c_qty")
    c_priority = st.selectbox("Priorité", ["Low", "Medium", "High"], index=2, key="c_prio")
    c_due = st.date_input("Échéance", value=date(2026, 3, 25), key="c_due")

    st.markdown("---")
    st.markdown("**Ajuster le stock**")
    st.caption("Simulez différents niveaux de stock.")

    custom_stock = {}
    for comp in BOM_FULL:
        needed = comp["qtyPerUnit"] * c_qty
        dflt = DEFAULT_STOCK.get(comp["itemCode"], 10)
        crit_icon = "🔴" if comp["isCritical"] else "⚪"
        custom_stock[comp["itemCode"]] = st.slider(
            f"{crit_icon} {comp['itemCode']} (besoin : {needed})",
            min_value=0, max_value=50, value=dflt,
            key=f"cs_{comp['itemCode']}",
        )

    custom_of = {
        "of_id": "of-custom-001", "scenario": "Custom",
        "scenario_label": "🔬 Custom + IA",
        "orderNumber": "OF-CUSTOM-001", "productCode": "BOGIE_Y32",
        "quantity": c_qty, "priority": c_priority,
        "status": st.session_state.get("custom_of_status", "Created"),
        "dueDate": f"{c_due.isoformat()}T00:00:00Z",
        "components": BOM_FULL, "stock": custom_stock, "historical_risk": "N/A",
    }
    st.session_state["orders"]["of-custom-001"] = custom_of

    st.markdown("---")
    cstock_rows = []
    for comp in BOM_FULL:
        needed = comp["qtyPerUnit"] * c_qty
        avail = custom_stock[comp["itemCode"]]
        cstock_rows.append({
            "Composant": comp["itemCode"], "Besoin": needed, "Dispo": avail,
            "Manque": max(0, needed - avail),
            "État": "✅" if avail >= needed else "❌",
        })
    st.dataframe(pd.DataFrame(cstock_rows), use_container_width=True, hide_index=True)

with custom_right:

    # ── Agent 1 Live ──────────────────────────────────────────
    st.markdown("#### 🚀 Agent 1 — Analyse de lancement (IA)")

    if st.button("Lancer Agent 1 (IA temps réel)", key="btn_a1_live", type="primary"):

        with st.status("🤖 Agent 1 en cours…", expanded=True) as status:
            st.write("📁 **1/5** — Calcul des besoins…")
            missing = _check_availability(BOM_FULL, c_qty, custom_stock)
            cutoff = _find_cutoff(ROUTING, missing)
            last_doable = _find_last_doable(ROUTING, cutoff)
            mvp = "FULL_RELEASE" if not missing else "PARTIAL_RELEASE"
            st.write(f"   → {len(missing)} manquant(s), décision déterministe : `{mvp}`")

            st.write("📝 **2/5** — Construction du prompt…")
            context = build_live_context_agent1(custom_of, custom_stock, missing, mvp, cutoff, last_doable)

            ai_analysis, raw_text = None, ""
            if env_ok:
                st.write("🧠 **3/5** — Appel LLM (10-30s)…")
                parsed, raw_text, error = call_llm(AGENT1_SYSTEM_PROMPT, context)
                if error:
                    st.write(f"   ⚠️ {error} — fallback déterministe")
                elif parsed:
                    ai_analysis = parsed
                    st.write(f"   ✅ `{parsed.get('decision', '?')}`")
            else:
                st.write("⏭️ **3/5** — LLM non configuré")

            st.write("📊 **4/5** — Décision finale…")
            decision = ai_analysis.get("decision", mvp) if ai_analysis else mvp
            if decision not in ("FULL_RELEASE", "PARTIAL_RELEASE", "DELAYED_RELEASE"):
                decision = mvp

            st.write("✅ **5/5** — Output…")
            now = datetime.now(timezone.utc).isoformat()
            output = {
                "of_id": "of-custom-001", "orderNumber": "OF-CUSTOM-001",
                "productCode": "BOGIE_Y32", "quantity": c_qty, "decision": decision,
                "previous_status": "Created", "timestamp": now,
                "ai_enhanced": ai_analysis is not None,
                "global_risk_score": (ai_analysis or {}).get("global_risk_score", 0),
                "risk_level": (ai_analysis or {}).get("risk_level", "N/A"),
                "risk_factors": (ai_analysis or {}).get("risk_factors", []),
                "recommended_start_slot": (ai_analysis or {}).get("recommended_start_slot"),
                "estimated_production_days": (ai_analysis or {}).get("estimated_production_days"),
                "sla_impact": (ai_analysis or {}).get("sla_impact", ""),
                "ai_reasoning": (ai_analysis or {}).get("reasoning", ""),
            }

            if decision == "FULL_RELEASE":
                output.update({"new_status": "Released", "missing_components": [],
                    "cutoff_operation": None, "resume_from_operation": None,
                    "instruction": "Production normale — tous les composants disponibles."})
            elif decision == "PARTIAL_RELEASE":
                output.update({"new_status": "PartiallyReleased", "missing_components": missing,
                    "cutoff_operation": ({"operationId": cutoff["operationId"], "sequence": cutoff["sequence"], "description": cutoff["description"]} if cutoff else None),
                    "resume_from_operation": ({"operationId": cutoff["operationId"], "sequence": cutoff["sequence"]} if cutoff else None),
                    "instruction": f"Produire jusqu'à {last_doable['operationId'] if last_doable else '?'}, puis attendre : {', '.join(mc['itemCode'] for mc in missing)}"})
            else:
                crit = [mc["itemCode"] for mc in missing if mc.get("isCritical")]
                output.update({"new_status": "Delayed", "missing_components": missing,
                    "cutoff_operation": None, "resume_from_operation": None,
                    "instruction": f"OF reporté — critiques manquants : {', '.join(crit) if crit else 'N/A'}."})

            st.session_state["agent1_outputs"]["of-custom-001"] = output
            custom_of["status"] = output["new_status"]
            custom_of["last_agent"] = "Agent 1"
            st.session_state["custom_of_status"] = output["new_status"]
            status.update(label="✅ Agent 1 terminé", state="complete")

        d, rl, rs = output["decision"], output["risk_level"], output["global_risk_score"]
        {"FULL_RELEASE": st.success, "PARTIAL_RELEASE": st.warning}.get(d, st.error)(
            f"{'✅' if d=='FULL_RELEASE' else '⚠️' if d=='PARTIAL_RELEASE' else '🛑'} **{d}** — Risque {rl} ({rs}/100)")
        st.markdown(f"**Consigne** : {output['instruction']}")
        if output.get("ai_reasoning"):
            with st.expander("💬 Explication IA"):
                st.write(output["ai_reasoning"])
        if raw_text:
            with st.expander("🔍 Réponse brute LLM"):
                st.code(raw_text, language="markdown")
        with st.expander("📝 Prompt envoyé"):
            st.code(context, language="markdown")
        with st.expander("🔧 Détail technique (JSON)"):
            st.json(output)

    elif "of-custom-001" in st.session_state.get("agent1_outputs", {}):
        prev = st.session_state["agent1_outputs"]["of-custom-001"]
        d, rl, rs = prev["decision"], prev["risk_level"], prev["global_risk_score"]
        {"FULL_RELEASE": st.success, "PARTIAL_RELEASE": st.warning}.get(d, st.error)(
            f"{'✅' if d=='FULL_RELEASE' else '⚠️' if d=='PARTIAL_RELEASE' else '🛑'} **{d}** — Risque {rl} ({rs}/100)")
        st.markdown(f"**Consigne** : {prev['instruction']}")
        with st.expander("🔧 Détail technique (JSON)"):
            st.json(prev)

    st.divider()

    # ── Agent 2 Live ──────────────────────────────────────────
    st.markdown("#### 🔍 Agent 2 — Pièces & reprise (IA)")
    st.caption("*Ajustez les curseurs de stock à gauche, puis relancez Agent 2.*")

    a1_custom = st.session_state.get("agent1_outputs", {}).get("of-custom-001")
    can_run_a2 = a1_custom and a1_custom.get("new_status") in ("PartiallyReleased", "Delayed")

    if not can_run_a2:
        st.caption("Disponible après Agent 1 en partiel ou report.")
    elif st.button("Lancer Agent 2 (IA temps réel)", key="btn_a2_live", type="primary"):

        with st.status("🤖 Agent 2…", expanded=True) as status2:
            st.write("📁 **1/4** — Stock vs manquants…")
            missing_from_a1 = a1_custom.get("missing_components", [])
            resolved, still_missing = [], []
            for mc in missing_from_a1:
                avail_now = custom_stock.get(mc["itemCode"], 0)
                if avail_now >= mc["qtyNeeded"]:
                    resolved.append({"itemCode": mc["itemCode"], "qtyNeeded": mc["qtyNeeded"], "qtyAvailableNow": avail_now})
                else:
                    still_missing.append({"itemCode": mc["itemCode"], "qtyNeeded": mc["qtyNeeded"],
                        "qtyAvailableNow": avail_now, "qtyStillShort": mc["qtyNeeded"] - avail_now,
                        "isCritical": mc.get("isCritical", False)})
            st.write(f"   → {len(resolved)} résolu(s), {len(still_missing)} manquant(s)")
            new_status = "ReadyToResume" if not still_missing else "PartiallyReleased"

            ai2, raw2 = None, ""
            if still_missing and env_ok:
                st.write("🧠 **2/4** — LLM reco fournisseur…")
                ctx2 = build_live_context_agent2("of-custom-001", c_priority, f"{c_due.isoformat()}", a1_custom, custom_stock, still_missing, resolved)
                parsed2, raw2, err2 = call_llm(AGENT2_SYSTEM_PROMPT, ctx2)
                if not err2 and parsed2:
                    ai2 = parsed2
                    st.write(f"   ✅ Priorité reprise : {parsed2.get('resume_priority', '?')}/5")
            elif still_missing:
                st.write("⏭️ **2/4** — LLM non configuré")
            else:
                st.write("✅ **2/4** — Toutes pièces dispo")

            st.write("📊 **3/4** — Output…")
            a2_output = {
                "of_id": "of-custom-001", "previous_status": custom_of["status"], "new_status": new_status,
                "resolved_components": resolved, "still_missing_components": still_missing,
                "timestamp": datetime.now(timezone.utc).isoformat(), "ai_enhanced": ai2 is not None,
                "resume_priority": (ai2 or {}).get("resume_priority"),
                "resume_priority_reasoning": (ai2 or {}).get("resume_priority_reasoning", ""),
                "supplier_recommendations": (ai2 or {}).get("supplier_recommendations", []),
                "overall_eta_days": (ai2 or {}).get("overall_eta_days"),
                "risk_assessment": (ai2 or {}).get("risk_assessment", ""),
                "ai_notification": (ai2 or {}).get("notification_text", ""),
            }
            resume_op = a1_custom.get("resume_from_operation", {})
            if new_status == "ReadyToResume" and resume_op:
                a2_output["resume_from_operation"] = resume_op
                a2_output["instruction"] = f"Reprendre à {resume_op.get('operationId', '?')}. Composants OK."
            else:
                a2_output["resume_from_operation"] = resume_op
                a2_output["instruction"] = f"Attente — {', '.join(sm['itemCode'] for sm in still_missing)}."

            st.write("✅ **4/4** — Persistance…")
            st.session_state["agent2_outputs"]["of-custom-001"] = a2_output
            custom_of["status"] = new_status
            custom_of["last_agent"] = "Agent 2"
            st.session_state["custom_of_status"] = new_status
            status2.update(label="✅ Agent 2 terminé", state="complete")

        if a2_output["new_status"] == "ReadyToResume":
            st.success(f"✅ **Prêt à reprendre** — {a2_output.get('resume_from_operation', {}).get('operationId', '?')}")
        else:
            st.warning(f"⏳ **En attente** — Priorité {a2_output.get('resume_priority', '?')}/5")
        st.markdown(f"**Consigne** : {a2_output['instruction']}")
        if a2_output.get("supplier_recommendations"):
            with st.expander("📦 Reco fournisseurs"):
                st.dataframe(pd.DataFrame(a2_output["supplier_recommendations"]), use_container_width=True, hide_index=True)
        if raw2:
            with st.expander("🔍 Réponse brute LLM"):
                st.code(raw2, language="markdown")
        with st.expander("🔧 Détail technique (JSON)"):
            st.json(a2_output)
