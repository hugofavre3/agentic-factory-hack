"""
Page 5 — Live Agent Runner

Interactive playground to run Maestro and Sentinel in real time
with modifiable inputs (WO parameters, stock levels, etc.).
"""

import streamlit as st
import pandas as pd
import sys
import os
import json
import copy
from datetime import date, datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data import (
    run_orchestrator, run_sentinelle,
    apply_operator_decision, refresh_watchlist,
    BOM_FULL, DEFAULT_STOCK, ROUTING, SUPPLIERS_DATA,
    HISTORICAL_OFS_DATA, MACHINE_CALENDAR_DATA, SLA_RULES_DATA,
    _check_availability, _find_cutoff, _find_last_doable, _find_risk_steps,
    _build_simulated_email,
    build_live_context_maestro, build_live_context_sentinelle,
    MAESTRO_SYSTEM_PROMPT, SENTINELLE_SYSTEM_PROMPT,
    call_llm, WORK_HOURS_PER_DAY,
)


# =============================================================================
# Live Maestro — fully deterministic, no scenario lookup
# =============================================================================

def _best_supplier(item_code):
    """Pick the best supplier for a component (reliability*0.4 + speed*0.35 + cost*0.25)."""
    candidates = [s for s in SUPPLIERS_DATA if item_code in s.get("components", [])]
    if not candidates:
        return None
    max_lead = max(s["leadTime_days"] for s in candidates) or 1
    max_price = max(s["unitPrice_eur"] for s in candidates) or 1
    scored = []
    for s in candidates:
        score = 0.40 * s["reliability"] + 0.35 * (1 - s["leadTime_days"] / max_lead) + 0.25 * (1 - s["unitPrice_eur"] / max_price)
        scored.append((score, s))
    scored.sort(key=lambda x: -x[0])
    return scored[0][1]


def run_maestro_live(of_id, orders):
    """Maestro analysis — fully computed from inputs (no simulated AI lookup)."""
    order = orders[of_id]
    components = order["components"]
    quantity = order["quantity"]
    stock = order["stock"]

    # Deterministic analysis
    missing = _check_availability(components, quantity, stock)
    cutoff_op = _find_cutoff(ROUTING, missing)
    last_doable = _find_last_doable(ROUTING, cutoff_op)
    risk_steps = _find_risk_steps(missing)

    due_date = datetime.fromisoformat(order["dueDate"].replace("Z", "+00:00"))
    now_dt = datetime.now(timezone.utc)
    days_until_due = (due_date - now_dt).days

    # --- Decide action ---
    if not missing:
        action = "LANCER_IMMEDIAT"
        risk_level = "VERT"
        score = max(5, min(20, 100 - days_until_due * 3))
        prob_blocage = 0
        delay_days = 0
        penalty = 0
    else:
        # Check if suppliers can deliver before blocking step
        longest_lead = 0
        has_unsourceable = False
        for mc in missing:
            sup = _best_supplier(mc["itemCode"])
            if sup:
                longest_lead = max(longest_lead, sup["leadTime_days"])
            else:
                has_unsourceable = True  # no known supplier for this part
        earliest_block = min((rs["time_to_reach_days"] for rs in risk_steps), default=0)
        nb_critical = sum(1 for mc in missing if mc.get("isCritical"))

        if len(missing) >= 3 or longest_lead > days_until_due or has_unsourceable:
            action = "REPORTER_ET_REPLANIFIER"
            risk_level = "ROUGE"
            score = min(98, 70 + len(missing) * 8)
            prob_blocage = min(99, 80 + nb_critical * 5)
            delay_days = max(1, longest_lead - days_until_due + 5)
            penalty = delay_days * 5000
        else:
            action = "LANCER_DECALE"
            risk_level = "ORANGE"
            score = min(75, 40 + len(missing) * 12)
            prob_blocage = min(60, 20 + len(missing) * 10)
            delay_days = 0
            penalty = 0

    # Etape a risque
    etape = None
    if risk_steps:
        rs = risk_steps[0]
        etape = {
            "operationId": rs["operationId"],
            "sequence": rs["sequence"],
            "description": rs["description"],
            "time_to_reach_days": rs["time_to_reach_days"],
            "composant_manquant": rs["itemCode"],
        }

    # Supplier plan
    supplier_plan = []
    simulated_emails = []
    today = now_dt
    for mc in missing:
        sup = _best_supplier(mc["itemCode"])
        if not sup:
            continue
        order_date = today.strftime("%Y-%m-%d")
        eta = (today + timedelta(days=sup["leadTime_days"])).strftime("%Y-%m-%d")
        eta_display = (today + timedelta(days=sup["leadTime_days"])).strftime("%d/%m/%Y")
        supplier_plan.append({
            "itemCode": mc["itemCode"],
            "recommended_supplier": sup["supplierId"],
            "supplier_name": sup["name"],
            "order_qty": mc["qtyShortage"],
            "unit_price_eur": sup["unitPrice_eur"],
            "total_price_eur": sup["unitPrice_eur"] * mc["qtyShortage"],
            "estimated_lead_days": sup["leadTime_days"],
            "order_date": order_date,
            "predicted_eta": eta,
            "confidence": sup["reliability"],
        })
        simulated_emails.append({
            "to": sup.get("contactEmail", sup.get("email", "")),
            "to_name": sup["name"],
            "supplier_id": sup["supplierId"],
            "subject": f"[URGENT] Order {mc['itemCode']} × {mc['qtyShortage']} — {order['orderNumber']}",
            "body": (
                f"Hello,\n\n"
                f"As part of {order['orderNumber']}, we have an urgent need "
                f"for {mc['qtyShortage']} unit(s) of {mc['itemCode']}.\n\n"
                f"Current stock: {mc['qtyAvailable']} / Requirement: {mc['qtyNeeded']}\n"
                f"Requested delivery date: {eta_display}\n"
                f"Impact if delayed: blockage at production step\n\n"
                f"Please confirm availability and delivery lead time.\n\n"
                f"Best regards,\nMaestro System — Alstom AI Planning"
            ),
        })

    # Rescheduling options (critical only)
    rescheduling_options = []
    if action == "REPORTER_ET_REPLANIFIER" and supplier_plan:
        etas = [datetime.strptime(p["predicted_eta"], "%Y-%m-%d") for p in supplier_plan]
        latest_eta = max(etas)
        due_naive = due_date.replace(tzinfo=None)
        launch_a = latest_eta
        completion_a = launch_a + timedelta(days=5)
        delay_a = max(0, (completion_a - due_naive).days)
        rescheduling_options.append({
            "label": f"Slot A — Launch on {launch_a.strftime('%d/%m')} morning",
            "slot": f"SLOT-{launch_a.strftime('%Y-%m-%d')}-AM",
            "launch_date": launch_a.strftime("%Y-%m-%d"),
            "estimated_completion": completion_a.strftime("%Y-%m-%d"),
            "delay_client_days": delay_a,
            "penalty_eur": delay_a * 5000,
            "comment": f"All parts available. {delay_a}-day delay.",
        })
        if len(etas) > 1:
            second = sorted(etas)[-2]
            if second < latest_eta:
                launch_b = second
                completion_b = launch_b + timedelta(days=5)
                delay_b = max(0, (completion_b - due_naive).days)
                rescheduling_options.append({
                    "label": f"Slot B — Launch on {launch_b.strftime('%d/%m')} (partial risk)",
                    "slot": f"SLOT-{launch_b.strftime('%Y-%m-%d')}-AM",
                    "launch_date": launch_b.strftime("%Y-%m-%d"),
                    "estimated_completion": completion_b.strftime("%Y-%m-%d"),
                    "delay_client_days": delay_b,
                    "penalty_eur": delay_b * 5000,
                    "comment": "Some parts available. Risk of blockage.",
                })

    # Messages
    if action == "LANCER_IMMEDIAT":
        msg = "All components available. No blocking risk. Proceed as planned."
        reasoning = f"Full stock verified. {days_until_due} days buffer before due date."
        sla_impact = "No SLA risk — delivery well ahead of due date."
        risk_factors = [
            {"factor": "Stock", "score": 5, "detail": "All components available"},
            {"factor": "Due date", "score": 5, "detail": f"{days_until_due} days of buffer"},
        ]
    elif action == "LANCER_DECALE":
        parts = ", ".join(mc["itemCode"] for mc in missing)
        msg = f"Missing parts ({parts}) but supplier ETA is within reach. Delayed launch recommended."
        reasoning = "\n".join(
            f"• {mc['itemCode']} — need {mc['qtyNeeded']}, have {mc['qtyAvailable']}, short {mc['qtyShortage']}"
            for mc in missing
        )
        sla_impact = "SLA at risk if supplier delays. Monitor closely."
        risk_factors = [
            {"factor": "Missing component", "score": score, "detail": parts},
            {"factor": "Supplier ETA", "score": min(60, longest_lead * 10), "detail": f"Longest lead: {longest_lead}d"},
            {"factor": "Due date", "score": max(20, 80 - days_until_due * 3), "detail": f"{days_until_due} days remaining"},
        ]
    else:
        parts = ", ".join(mc["itemCode"] for mc in missing)
        msg = f"Critical shortage ({parts}). Rescheduling strongly recommended."
        reasoning = "\n".join(
            f"• {mc['itemCode']} — need {mc['qtyNeeded']}, have {mc['qtyAvailable']}, short {mc['qtyShortage']}"
            for mc in missing
        )
        sla_impact = f"SLA compromised — due in {days_until_due}d, replenishment {longest_lead}d. Penalties: €{penalty:,}."
        risk_factors = [
            {"factor": "Missing critical components", "score": score, "detail": f"{len(missing)} parts unavailable"},
            {"factor": "Lead time vs due date", "score": min(98, longest_lead * 7), "detail": f"{longest_lead}d replenishment, {days_until_due}d remaining"},
            {"factor": "Delay history", "score": 70, "detail": "Historical delays on similar WOs"},
        ]

    # Recommended slot
    launch_date = None
    launch_slot = None
    if action == "LANCER_IMMEDIAT":
        for slot in MACHINE_CALENDAR_DATA:
            if slot["status"] == "available":
                launch_date = slot["date"]
                launch_slot = slot["slotId"]
                break
    elif action == "LANCER_DECALE" and supplier_plan:
        best_eta = max(sp["predicted_eta"] for sp in supplier_plan)
        launch_date = best_eta
        launch_slot = f"SLOT-{best_eta}-AM"

    output = {
        "of_id": of_id,
        "orderNumber": order["orderNumber"],
        "productCode": order["productCode"],
        "quantity": quantity,
        "timestamp": now_dt.isoformat(),
        "risk_level": risk_level,
        "global_risk_score": score,
        "probabilite_blocage_pct": prob_blocage,
        "etape_a_risque": etape,
        "risk_steps": risk_steps,
        "recommended_action": action,
        "recommended_launch_date": launch_date,
        "recommended_launch_slot": launch_slot,
        "estimated_production_days": 5,
        "days_until_due": days_until_due,
        "estimated_delay_days": delay_days,
        "estimated_penalty_eur": penalty,
        "maestro_message": msg,
        "reasoning": reasoning,
        "risk_factors": risk_factors,
        "sla_impact": sla_impact,
        "supplier_order_plan": supplier_plan,
        "simulated_emails": simulated_emails,
        "rescheduling_options": rescheduling_options,
        "missing_components": missing,
        "cutoff_operation": {
            "operationId": cutoff_op["operationId"],
            "sequence": cutoff_op["sequence"],
            "description": cutoff_op["description"],
        } if cutoff_op else None,
        "operator_decision": None,
        "previous_status": order["status"],
        "new_status": "AwaitingDecision",
    }
    order["status"] = "AwaitingDecision"
    order["last_agent"] = "Maestro"
    return output


st.set_page_config(page_title="Live Agent Runner", page_icon="🧪", layout="wide")

TODAY = date(2026, 3, 13)


# =============================================================================
# Session state init
# =============================================================================
if "live_maestro_output" not in st.session_state:
    st.session_state["live_maestro_output"] = None
if "live_sentinelle_output" not in st.session_state:
    st.session_state["live_sentinelle_output"] = None
if "live_llm_raw" not in st.session_state:
    st.session_state["live_llm_raw"] = None


# =============================================================================
# Header
# =============================================================================
st.markdown(
    "<h1 style='text-align:center;'>🧪 Live Agent Runner</h1>"
    "<p style='text-align:center; color:#888;'>"
    "Run Maestro & Sentinel interactively with custom inputs</p>",
    unsafe_allow_html=True,
)
st.markdown("---")


# =============================================================================
# Sidebar — Input configuration
# =============================================================================
st.sidebar.header("📝 Work Order Configuration")

of_id = st.sidebar.text_input("Work Order ID", value="of-2026-00123")
of_number = st.sidebar.text_input("Order Number", value=f"OF-{of_id.replace('of-', '')}")
product_code = st.sidebar.selectbox("Product", ["BOGIE_Y32"], index=0)
quantity = st.sidebar.number_input("Quantity", min_value=1, max_value=20, value=4)
priority = st.sidebar.selectbox("Priority", ["Low", "Medium", "High"], index=2)
due_date = st.sidebar.date_input("Due Date", value=date(2026, 3, 25))

st.sidebar.markdown("---")
st.sidebar.header("📦 Stock Levels")

stock_inputs = {}
for comp in BOM_FULL:
    default_val = DEFAULT_STOCK.get(comp["itemCode"], 0)
    stock_inputs[comp["itemCode"]] = st.sidebar.number_input(
        f"{comp['itemCode']} {'🔴' if comp.get('isCritical') else '⚪'}",
        min_value=0,
        max_value=200,
        value=default_val,
        key=f"stock_{comp['itemCode']}",
    )


# =============================================================================
# Build the custom order object (same schema as build_seed_orders)
# =============================================================================
def build_custom_order():
    return {
        of_id: {
            "of_id": of_id,
            "scenario": "Custom",
            "scenario_label": "🧪 Custom — Live input",
            "orderNumber": of_number,
            "productCode": product_code,
            "quantity": quantity,
            "priority": priority,
            "status": "Created",
            "dueDate": f"{due_date.isoformat()}T00:00:00Z",
            "components": copy.deepcopy(BOM_FULL),
            "stock": dict(stock_inputs),
            "historical_risk": "CUSTOM",
        }
    }


# =============================================================================
# Main area — tabs
# =============================================================================
tab_config, tab_maestro, tab_sentinel, tab_json = st.tabs([
    "⚙️ Preview", "🎼 Maestro", "🛡️ Sentinel", "📄 JSON Output"
])


# ─── Preview tab ─────────────────────────────────────────────────────────────
with tab_config:
    st.subheader("Work Order Preview")

    col1, col2, col3 = st.columns(3)
    col1.metric("WO ID", of_id)
    col2.metric("Quantity", quantity)
    days_left = (due_date - TODAY).days
    col3.metric("Days until due", days_left)

    st.markdown("#### Component Availability")
    rows = []
    for comp in BOM_FULL:
        needed = comp["qtyPerUnit"] * quantity
        avail = stock_inputs.get(comp["itemCode"], 0)
        shortage = max(0, needed - avail)
        status = "✅ OK" if avail >= needed else "❌ Missing"
        rows.append({
            "Component": comp["itemCode"],
            "Critical": "🔴" if comp.get("isCritical") else "⚪",
            "Needed": needed,
            "Available": avail,
            "Shortage": shortage,
            "Status": status,
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    missing = [r for r in rows if r["Shortage"] > 0]
    if not missing:
        st.success("All components available — Maestro should recommend LANCER_IMMEDIAT")
    elif len(missing) == 1:
        st.warning(f"1 component missing ({missing[0]['Component']}) — likely LANCER_DECALE")
    else:
        parts = ", ".join(m["Component"] for m in missing)
        st.error(f"{len(missing)} components missing ({parts}) — likely REPORTER_ET_REPLANIFIER")

    st.markdown("#### Routing")
    missing_codes = {r["Component"] for r in rows if r["Shortage"] > 0}
    route_rows = []
    for op in ROUTING:
        req = set(op.get("requiredComponents", []))
        blocked = req & missing_codes
        days_to = round(op["cumulative_start_hours"] / WORK_HOURS_PER_DAY, 1)
        route_rows.append({
            "Seq": op["sequence"],
            "Operation": op["operationId"],
            "Description": op["description"],
            "Duration (h)": op["duration_hours"],
            "Reached in (days)": days_to,
            "Status": "🔴 BLOCKED" if blocked else "🟢 OK",
            "Blocked by": ", ".join(blocked) if blocked else "—",
        })
    st.dataframe(pd.DataFrame(route_rows), use_container_width=True, hide_index=True)


# ─── Maestro tab ─────────────────────────────────────────────────────────────
with tab_maestro:
    st.subheader("🎼 Run Maestro")
    st.markdown("Maestro analyzes the work order and produces a launch/reschedule recommendation.")

    col_mode1, col_mode2 = st.columns(2)
    use_llm_maestro = col_mode1.checkbox("Use Azure AI (LLM)", value=False, key="llm_maestro")

    if st.button("▶️ Run Maestro", type="primary", key="btn_maestro"):
        orders = build_custom_order()
        with st.spinner("Maestro is analyzing..."):
            maestro_output = run_maestro_live(of_id, orders)
            st.session_state["live_maestro_output"] = maestro_output
            st.session_state["live_orders"] = orders

            # If LLM mode, also call the LLM
            if use_llm_maestro:
                order_data = orders[of_id]
                missing_comps = _check_availability(
                    order_data["components"], order_data["quantity"], order_data["stock"]
                )
                cutoff = _find_cutoff(ROUTING, missing_comps)
                last_doable = _find_last_doable(ROUTING, cutoff)
                context = build_live_context_maestro(
                    order_data, order_data["stock"], missing_comps, cutoff, last_doable
                )
                parsed, raw, error = call_llm(MAESTRO_SYSTEM_PROMPT, context)
                st.session_state["live_llm_raw"] = {"maestro": {"parsed": parsed, "raw": raw, "error": error}}
        st.rerun()

    output = st.session_state.get("live_maestro_output")
    if output:
        # Risk banner
        risk = output.get("risk_level", "?")
        score = output.get("global_risk_score", "?")
        action = output.get("recommended_action", "?")
        color_map = {"VERT": "#27ae60", "ORANGE": "#f39c12", "ROUGE": "#e74c3c"}
        color = color_map.get(risk, "#888")

        st.markdown(
            f"<div style='padding:16px; background:{color}22; border-left:4px solid {color}; "
            f"border-radius:8px; margin-bottom:16px;'>"
            f"<b style='color:{color}; font-size:1.3em;'>{risk}</b> — "
            f"Score: {score}/100 — Action: <code>{action}</code></div>",
            unsafe_allow_html=True,
        )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Risk Score", f"{score}/100")
        c2.metric("Blocking Prob.", f"{output.get('probabilite_blocage_pct', 0)}%")
        c3.metric("Est. Delay", f"{output.get('estimated_delay_days', 0)}d")
        c4.metric("Est. Penalty", f"{output.get('estimated_penalty_eur', 0):,}€")

        st.markdown("#### 💬 Maestro Message")
        st.info(output.get("maestro_message", "—"))

        if output.get("reasoning"):
            with st.expander("🧠 Detailed Reasoning"):
                st.markdown(output["reasoning"])

        if output.get("risk_factors"):
            st.markdown("#### Risk Factors")
            rf_df = pd.DataFrame(output["risk_factors"])
            st.dataframe(rf_df, use_container_width=True, hide_index=True)

        if output.get("missing_components"):
            st.markdown("#### ❌ Missing Components")
            mc_rows = []
            for mc in output["missing_components"]:
                mc_rows.append({
                    "Component": mc["itemCode"],
                    "Critical": "🔴" if mc.get("isCritical") else "⚪",
                    "Needed": mc["qtyNeeded"],
                    "Available": mc["qtyAvailable"],
                    "Shortage": mc["qtyShortage"],
                })
            st.dataframe(pd.DataFrame(mc_rows), use_container_width=True, hide_index=True)

        if output.get("etape_a_risque"):
            st.markdown("#### ⚠️ At-Risk Step")
            etape = output["etape_a_risque"]
            st.warning(
                f"**{etape['operationId']}** ({etape['description']}) — "
                f"reached in {etape['time_to_reach_days']} days — "
                f"missing: {etape['composant_manquant']}"
            )

        if output.get("supplier_order_plan"):
            st.markdown("#### 📦 Supplier Order Plan")
            sp_df = pd.DataFrame(output["supplier_order_plan"])
            cols_to_show = ["itemCode", "supplier_name", "order_qty", "unit_price_eur",
                            "total_price_eur", "estimated_lead_days", "predicted_eta", "confidence"]
            available_cols = [c for c in cols_to_show if c in sp_df.columns]
            st.dataframe(sp_df[available_cols], use_container_width=True, hide_index=True)

        if output.get("simulated_emails"):
            st.markdown("#### ✉️ Simulated Supplier Emails")
            for email in output["simulated_emails"]:
                with st.expander(f"📧 {email.get('subject', 'Email')}"):
                    st.text(f"To: {email.get('to_name', '?')} <{email.get('to', '?')}>")
                    st.text(email.get("body", ""))

        if output.get("rescheduling_options"):
            st.markdown("#### 📅 Rescheduling Options")
            for opt in output["rescheduling_options"]:
                st.markdown(
                    f"- **{opt['label']}** — Launch: {opt['launch_date']}, "
                    f"Completion: {opt['estimated_completion']}, "
                    f"Delay: +{opt['delay_client_days']}d, "
                    f"Penalty: {opt['penalty_eur']:,}€"
                )

        if output.get("sla_impact"):
            st.markdown("#### 📊 SLA Impact")
            st.markdown(output["sla_impact"])

        # LLM results
        llm_data = (st.session_state.get("live_llm_raw") or {}).get("maestro")
        if llm_data:
            st.markdown("---")
            st.markdown("#### 🤖 LLM Response")
            if llm_data.get("error"):
                st.error(llm_data["error"])
            else:
                if llm_data.get("parsed"):
                    with st.expander("Parsed JSON from LLM"):
                        st.json(llm_data["parsed"])
                if llm_data.get("raw"):
                    with st.expander("Raw LLM response"):
                        st.code(llm_data["raw"], language="markdown")


# ─── Sentinel tab ────────────────────────────────────────────────────────────
with tab_sentinel:
    st.subheader("🛡️ Run Sentinel")
    st.markdown(
        "Sentinel checks whether parts have arrived and updates the risk. "
        "**Run Maestro first**, then decide an action, then run Sentinel."
    )

    maestro_out = st.session_state.get("live_maestro_output")
    if not maestro_out:
        st.warning("Run Maestro first to generate the output that Sentinel monitors.")
    else:
        st.markdown("#### Operator Decision")
        st.markdown(
            f"Maestro recommended: **{maestro_out.get('recommended_action', '?')}**. "
            "Choose the operator decision to apply before running Sentinel:"
        )
        decision = st.radio(
            "Decision",
            ["LANCER_IMMEDIAT", "LANCER_DECALE", "REPORTER_ET_REPLANIFIER"],
            index=1 if maestro_out.get("recommended_action") == "LANCER_DECALE"
                  else 2 if maestro_out.get("recommended_action") == "REPORTER_ET_REPLANIFIER"
                  else 0,
            horizontal=True,
            key="sentinel_decision",
        )

        st.markdown("---")
        st.markdown("#### 📦 Simulated Stock Update (for Sentinel)")
        st.markdown("Adjust the stock to simulate parts arrivals before running Sentinel:")

        sentinel_stock = {}
        missing_items = {mc["itemCode"] for mc in (maestro_out.get("missing_components") or [])}
        for comp in BOM_FULL:
            default = stock_inputs.get(comp["itemCode"], 0)
            # If part was missing and Maestro ordered it, suggest a higher stock
            if comp["itemCode"] in missing_items:
                supplier_plan = maestro_out.get("supplier_order_plan", [])
                ordered_qty = sum(
                    sp["order_qty"] for sp in supplier_plan if sp["itemCode"] == comp["itemCode"]
                )
                sentinel_stock[comp["itemCode"]] = st.number_input(
                    f"{comp['itemCode']} (was {default}, ordered {ordered_qty})",
                    min_value=0, max_value=200, value=default,
                    key=f"sentinel_stock_{comp['itemCode']}",
                )
            else:
                sentinel_stock[comp["itemCode"]] = default

        use_llm_sentinel = st.checkbox("Use Azure AI (LLM)", value=False, key="llm_sentinel")

        if st.button("▶️ Run Sentinel", type="primary", key="btn_sentinel"):
            # Build orders and run the pipeline
            orders = st.session_state.get("live_orders", build_custom_order())
            # Update stock in order
            orders[of_id]["stock"] = dict(sentinel_stock)
            # Apply operator decision
            maestro_outputs = {of_id: maestro_out}
            apply_operator_decision(of_id, orders, maestro_outputs, decision)

            # Run orchestrator
            watchlist = run_orchestrator(maestro_outputs, orders)

            if not watchlist:
                st.session_state["live_sentinelle_output"] = {
                    "message": "No WOs in watchlist — Maestro decision doesn't require monitoring.",
                    "results": [],
                }
            else:
                with st.spinner("Sentinel is checking parts..."):
                    results = run_sentinelle(orders, maestro_outputs, watchlist)
                    st.session_state["live_sentinelle_output"] = {"results": results}

                    # Optional LLM enrichment
                    if use_llm_sentinel and results:
                        r = results[0]
                        context = build_live_context_sentinelle(
                            of_id, orders[of_id].get("priority", "N/A"),
                            orders[of_id].get("dueDate", "N/A"),
                            maestro_out, sentinel_stock,
                            r.get("still_missing_components", []),
                            r.get("resolved_components", []),
                        )
                        parsed, raw, error = call_llm(SENTINELLE_SYSTEM_PROMPT, context)
                        st.session_state["live_llm_raw"] = st.session_state.get("live_llm_raw") or {}
                        st.session_state["live_llm_raw"]["sentinel"] = {
                            "parsed": parsed, "raw": raw, "error": error
                        }
            st.rerun()

        sentinel_data = st.session_state.get("live_sentinelle_output")
        if sentinel_data:
            if sentinel_data.get("message"):
                st.info(sentinel_data["message"])

            for result in sentinel_data.get("results", []):
                risk = result.get("current_risk_level", "?")
                evo = result.get("risk_evolution", "?")
                warning = result.get("warning_status", "?")
                color_map = {"VERT": "#27ae60", "ORANGE": "#f39c12", "ROUGE": "#e74c3c"}
                color = color_map.get(risk, "#888")

                st.markdown(
                    f"<div style='padding:16px; background:{color}22; border-left:4px solid {color}; "
                    f"border-radius:8px; margin-bottom:16px;'>"
                    f"<b style='color:{color}; font-size:1.3em;'>{risk}</b> — "
                    f"Evolution: {evo} — Warning: <code>{warning}</code></div>",
                    unsafe_allow_html=True,
                )

                c1, c2, c3 = st.columns(3)
                c1.metric("Status", result.get("new_status", "?"))
                c2.metric("Delay", f"{result.get('updated_delay_days', 0)}d")
                c3.metric("Resume Priority", f"{result.get('resume_priority', '?')}/5")

                st.markdown("#### 💬 Sentinel Message")
                if result.get("new_status") == "RiskCleared":
                    st.success(result.get("sentinelle_message", ""))
                else:
                    st.warning(result.get("sentinelle_message", ""))

                if result.get("parts_tracking"):
                    st.markdown("#### 📦 Parts Tracking")
                    pt_df = pd.DataFrame(result["parts_tracking"])
                    st.dataframe(pt_df, use_container_width=True, hide_index=True)

                if result.get("resolved_components"):
                    st.markdown("#### ✅ Resolved Components")
                    for r in result["resolved_components"]:
                        st.markdown(f"- **{r['itemCode']}** — available {r['qtyAvailableNow']} ≥ need {r['qtyNeeded']}")

                if result.get("still_missing_components"):
                    st.markdown("#### ❌ Still Missing")
                    sm_df = pd.DataFrame(result["still_missing_components"])
                    st.dataframe(sm_df, use_container_width=True, hide_index=True)

                if result.get("rescheduling_proposal"):
                    st.markdown("#### 📅 Rescheduling Proposal")
                    prop = result["rescheduling_proposal"]
                    st.markdown(
                        f"- **{prop.get('label', '?')}** — Launch: {prop.get('launch_date', '?')}, "
                        f"Completion: {prop.get('estimated_completion', '?')}, "
                        f"Delay: +{prop.get('delay_client_days', '?')}d, "
                        f"Penalty: {prop.get('penalty_eur', '?'):,}€"
                    )

                if result.get("supplier_recommendations"):
                    st.markdown("#### 📦 Supplier Recommendations")
                    sr_df = pd.DataFrame(result["supplier_recommendations"])
                    st.dataframe(sr_df, use_container_width=True, hide_index=True)

            # LLM results
            llm_data = (st.session_state.get("live_llm_raw") or {}).get("sentinel")
            if llm_data:
                st.markdown("---")
                st.markdown("#### 🤖 LLM Response")
                if llm_data.get("error"):
                    st.error(llm_data["error"])
                else:
                    if llm_data.get("parsed"):
                        with st.expander("Parsed JSON from LLM"):
                            st.json(llm_data["parsed"])
                    if llm_data.get("raw"):
                        with st.expander("Raw LLM response"):
                            st.code(llm_data["raw"], language="markdown")


# ─── JSON Output tab ─────────────────────────────────────────────────────────
with tab_json:
    st.subheader("📄 Raw JSON Outputs")

    maestro_json = st.session_state.get("live_maestro_output")
    sentinel_json = st.session_state.get("live_sentinelle_output")

    if maestro_json:
        st.markdown("#### Maestro Output")
        st.json(maestro_json)
    else:
        st.info("Run Maestro to see the raw output.")

    if sentinel_json and sentinel_json.get("results"):
        st.markdown("#### Sentinel Output")
        for r in sentinel_json["results"]:
            st.json(r)
    else:
        st.info("Run Sentinel to see the raw output.")
