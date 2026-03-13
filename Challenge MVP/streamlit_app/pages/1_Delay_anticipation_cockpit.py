"""
Page 1 — Delay anticipation cockpit


Main operational view of the demonstration.
This page allows you to visualize, production order by production order:
- the days remaining before the due date,
- the production flow and the potentially critical step,
- the risk level estimated by Maestro,
- the dynamic monitoring provided by Sentinelle,
- the impact of decisions on the forecast delay.
"""


import streamlit as st
import pandas as pd
import sys, os
from datetime import date, datetime, timezone, timedelta



sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data import (
    run_maestro, run_orchestrator, run_sentinelle, build_seed_orders,
    apply_operator_decision, apply_email_action, apply_rescheduling_choice,
    advance_time, refresh_watchlist,
    BOM_FULL, DEFAULT_STOCK, ROUTING, SUPPLIERS_DATA,
    HISTORICAL_OFS_DATA, MACHINE_CALENDAR_DATA, SLA_RULES_DATA,
    _check_availability, _find_cutoff, _find_last_doable, _find_risk_steps,
    build_live_context_maestro, build_live_context_sentinelle,
    MAESTRO_SYSTEM_PROMPT, SENTINELLE_SYSTEM_PROMPT,
    call_llm, get_stock_updates_preview, resume_of,
    WORK_HOURS_PER_DAY,
)



st.set_page_config(page_title="Anticipation cockpit", page_icon="📋", layout="wide")



# --- Init ---
for key, default in [
    ("orders", None), ("maestro_outputs", {}), ("sentinelle_outputs", {}),
    ("watchlist", []), ("email_actions", {}), ("time_sim_results", {}),
    ("rescheduling_choices", {}),
]:
    if key not in st.session_state:
        st.session_state[key] = build_seed_orders() if key == "orders" else default



orders = st.session_state["orders"]
sim_orders = {k: v for k, v in orders.items() if k != "of-custom-001"}



TODAY = date(2026, 3, 13)
NOW_UTC = datetime(2026, 3, 13, tzinfo=timezone.utc)




# =============================================================================
# Helper — remaining days color
# =============================================================================



def days_remaining_style(days_left):
    """Returns (icon, CSS color) depending on the time remaining before the due date."""
    if days_left >= 15:
        return "🟢", "#2ecc71"
    elif days_left >= 8:
        return "🟠", "#f39c12"
    else:
        return "🔴", "#e74c3c"



def risk_color(level):
    colors = {"VERT": "#2ecc71", "ORANGE": "#f39c12", "ROUGE": "#e74c3c"}
    return colors.get(level, "#95a5a6")




# =============================================================================
# Header: Current date
# =============================================================================



st.markdown(
    f"<div style='text-align:center; padding:12px; background:linear-gradient(90deg,#1a1a2e,#16213e); "
    f"border-radius:10px; margin-bottom:12px;'>"
    f"<span style='font-size:1.5em; color:white;'>📅 Current date: <b>{TODAY.strftime('%d/%m/%Y')}</b></span>"
    f"</div>",
    unsafe_allow_html=True,
)



st.title("📋 Delay anticipation cockpit")
st.caption(
    "This view makes it possible to identify, for each production order, **how many days remain**, "
    "**at which step a blockage could occur**, and whether the parts have a realistic chance "
    "of arriving before production reaches that critical point."
)



# =============================================================================
# KPIs — with calculation methodology
# =============================================================================



st.divider()



maestro_outs = st.session_state["maestro_outputs"]
sentinelle_outs = st.session_state["sentinelle_outputs"]
time_sim = st.session_state["time_sim_results"]
total_of = len(sim_orders)



of_at_risk = sum(
    1 for of_id in sim_orders
    if maestro_outs.get(of_id, {}).get("risk_level") in ("ORANGE", "ROUGE")
    and sentinelle_outs.get(of_id, {}).get("warning_status") != "LEVE"
)


of_ok = sum(
    1 for of_id in sim_orders
    if maestro_outs.get(of_id, {}).get("risk_level") == "VERT"
    or sentinelle_outs.get(of_id, {}).get("warning_status") == "LEVE"
)


delay_avoided = sum(
    maestro_outs.get(of_id, {}).get("estimated_delay_days", 0)
    for of_id in sim_orders
    if sentinelle_outs.get(of_id, {}).get("warning_status") == "LEVE"
)



# Minimum remaining days (worst case)
all_days_left = []
for of_id, order in sim_orders.items():
    due_dt = datetime.fromisoformat(order["dueDate"].replace("Z", "+00:00"))
    dl = (due_dt - NOW_UTC).days
    all_days_left.append((of_id, dl))



worst_days = min(all_days_left, key=lambda x: x[1]) if all_days_left else ("—", 99)
worst_icon, worst_color = days_remaining_style(worst_days[1])



# KPI display
kpi_cols = st.columns(4)



with kpi_cols[0]:
    st.metric("⚠️ Production orders under watch", of_at_risk)
    st.caption("Method: production orders whose Maestro risk is orange or red, and whose alert has not yet been cleared by Sentinelle.")


with kpi_cols[1]:
    st.metric("✅ Secured production orders", of_ok)
    st.caption("Method: production orders assessed as green by Maestro, or production orders whose risk has been cleared by Sentinelle.")


with kpi_cols[2]:
    st.metric("⏱️ Estimated delay avoided", f"{delay_avoided} d")
    st.caption("Method: sum of the delay days estimated by Maestro for production orders whose risk was ultimately cleared.")


with kpi_cols[3]:
    st.metric("📦 Production orders tracked", total_of)
    st.caption("Method: total number of production orders within the demonstration scope.")




# =============================================================================
# Input data — with exploration buttons
# =============================================================================



st.divider()
st.subheader("📂 Data used by the agents")
st.caption(
    "Maestro and Sentinelle rely on this data to analyze blocking risks, "
    "estimate potential delays, and recommend the right actions."
)



inp_col1, inp_col2, inp_col3, inp_col4 = st.columns(4)



with inp_col1:
    with st.expander("📦 Current stock"):
        stock_rows = []
        for comp in BOM_FULL:
            default_qty = DEFAULT_STOCK.get(comp["itemCode"], 0)
            crit = "🔴" if comp["isCritical"] else "⚪"
            stock_rows.append({
                "Component": comp["itemCode"],
                "Description": comp["description"],
                "Stock": default_qty,
                "Critical": crit,
            })
        st.dataframe(pd.DataFrame(stock_rows), use_container_width=True, hide_index=True)



with inp_col2:
    with st.expander("🔧 Routing and production steps"):
        routing_rows = []
        for op in ROUTING:
            days = round(op["cumulative_start_hours"] / WORK_HOURS_PER_DAY, 1)
            routing_rows.append({
                "Seq.": op["sequence"],
                "Operation": op["operationId"],
                "Description": op["description"],
                "Duration (h)": op["duration_hours"],
                "Reached from (d)": days,
                "Required components": ", ".join(op["requiredComponents"]) or "—",
            })
        st.dataframe(pd.DataFrame(routing_rows), use_container_width=True, hide_index=True)



with inp_col3:
    with st.expander("🚚 Supplier master data"):
        sup_rows = []
        for s in SUPPLIERS_DATA:
            sup_rows.append({
                "Supplier": s["name"],
                "Covered components": ", ".join(s["components"]),
                "Estimated lead time (d)": s["leadTime_days"],
                "Reliability": f"{s['reliability']*100:.0f}%",
                "Unit price": f"{s['unitPrice_eur']}€",
            })
        st.dataframe(pd.DataFrame(sup_rows), use_container_width=True, hide_index=True)



with inp_col4:
    with st.expander("📋 Bill of materials (BOM)"):
        bom_rows = []
        for comp in BOM_FULL:
            bom_rows.append({
                "Code": comp["itemCode"],
                "Description": comp["description"],
                "Qty / unit": comp["qtyPerUnit"],
                "Critical": "🔴 Yes" if comp["isCritical"] else "No",
            })
        st.dataframe(pd.DataFrame(bom_rows), use_container_width=True, hide_index=True)



# Input row 2
inp2_col1, inp2_col2, inp2_col3 = st.columns(3)



with inp2_col1:
    with st.expander("📊 History of similar cases"):
        hist_rows = []
        for h in HISTORICAL_OFS_DATA:
            hist_rows.append({
                "Production order": h["of_id"],
                "Qty": h["quantity"],
                "Observed delay (d)": h["daysLate"],
                "Blockage observed at": h.get("blockedAtStep") or "—",
                "Blocking components": ", ".join(h["blockedComponents"]) or "—",
            })
        st.dataframe(pd.DataFrame(hist_rows), use_container_width=True, hide_index=True)



with inp2_col2:
    with st.expander("🗓️ Workshop / machine calendar"):
        cal_rows = []
        for slot in MACHINE_CALENDAR_DATA:
            cal_rows.append({
                "Slot": slot["slotId"],
                "Date": slot["date"],
                "Shift": slot["shift"],
                "Load": f"{slot['currentLoad']*100:.0f}%",
                "Status": slot["status"],
            })
        st.dataframe(pd.DataFrame(cal_rows), use_container_width=True, hide_index=True)



with inp2_col3:
    with st.expander("📜 SLA / customer constraints"):
        sla_rows = []
        for rule in SLA_RULES_DATA:
            sla_rows.append({
                "Customer": rule["client"],
                "Service level": rule["serviceLevelAgreement"],
                "Max tolerated delay": f"{rule['maxAcceptableDelay_days']} d",
                "Penalty": f"{rule['penaltyPerDayLate_eur']}€/d",
            })
        st.dataframe(pd.DataFrame(sla_rows), use_container_width=True, hide_index=True)




# =============================================================================
# Central table — production orders, remaining days, step-by-step risks
# =============================================================================



st.divider()
st.subheader("📊 Production orders and step-by-step risks")
st.caption(
    "Each row makes it possible to understand whether a production order is under control, under watch, or critical, "
    "and at which routing step a blockage could occur if the parts do not arrive on time."
)



rows = []
for of_id, order in sim_orders.items():
    m = maestro_outs.get(of_id, {})
    s = sentinelle_outs.get(of_id, {})
    ts = time_sim.get(of_id, {})


    # Core business data
    etape = m.get("etape_a_risque")
    etape_label = etape["operationId"] if etape else "None"
    prob_blocage = m.get("probabilite_blocage_pct", "—")
    delay = m.get("estimated_delay_days", "—")


    # Remaining days
    due_dt = datetime.fromisoformat(order["dueDate"].replace("Z", "+00:00"))
    days_left = (due_dt - NOW_UTC).days


    # Effective warning = only Sentinelle can clear/confirm the risk
    effective_warning = s.get("warning_status")


    # Effective risk recalculated with Sentinelle only
    if effective_warning == "LEVE":
        effective_risk = "VERT"
    elif effective_warning == "CONFIRME":
        effective_risk = "ROUGE"
    else:
        effective_risk = m.get("risk_level", "—")


    # Delay: Sentinelle takes priority if available
    effective_delay = s.get("updated_delay_days", delay)


    # Maestro status
    action = m.get("recommended_action", "—")
    action_labels = {
        "LANCER_IMMEDIAT": "✅ Launch recommended",
        "LANCER_DECALE": "⚠️ Launch to be adjusted",
        "REPORTER_ET_REPLANIFIER": "🛑 Rescheduling recommended",
    }
    maestro_status = action_labels.get(action, "🔵 Not analyzed")


    # Effective Sentinelle status
    sentinelle_status_labels = {
        "LEVE": "✅ Risk cleared",
        "CONFIRME": "🔴 Risk confirmed",
        "EN_SURVEILLANCE": "🔍 Risk under monitoring",
    }
    sentinelle_status = sentinelle_status_labels.get(effective_warning, "—")


    # Risk icon
    risk_icons = {"VERT": "🟢", "ORANGE": "🟠", "ROUGE": "🔴"}
    risk_icon = risk_icons.get(effective_risk, "⚪")


    # Optional: timing readout parts vs step
    timing = "—"
    if etape and m.get("supplier_order_plan"):
        relevant = [
            p for p in m["supplier_order_plan"]
            if p["itemCode"] == etape.get("composant_manquant")
        ]
        if relevant:
            eta = relevant[0]["estimated_lead_days"]
            reach = etape["time_to_reach_days"]
            if eta <= reach:
                timing = f"✅ Part expected before the critical step (D+{eta} < D+{reach})"
            else:
                timing = f"⚠️ Part expected after the critical step (D+{eta} > D+{reach})"
    elif effective_risk == "VERT":
        timing = "✅ No material tension identified"


    rows.append({
        "Production order": order["orderNumber"],
        "Product": order["productCode"],
        "Qty": order["quantity"],
        "Due date": order["dueDate"][:10],
        "Days left": days_left,
        "Risk": f"{risk_icon} {effective_risk}",
        "Step at risk": etape_label,
        "Blocking prob.": f"{prob_blocage}%" if isinstance(prob_blocage, (int, float)) else prob_blocage,
        "Estimated delay": f"{effective_delay} d" if isinstance(effective_delay, (int, float)) else effective_delay,
        "Maestro": maestro_status,
        "Sentinelle": sentinelle_status,
        "Parts vs step": timing,
    })



if rows:
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.info("No production order is currently loaded in the demonstration.")

st.divider()
st.subheader("⚡ Analyze a production order and anticipate its delay risk")



left, right = st.columns([1, 2])



with left:
    st.markdown("**Choose a demonstration scenario**")
    scenario_labels = {of["of_id"]: of["scenario_label"] for of in sim_orders.values()}
    selected_of_id = st.radio(
        "Choose a production order:",
        options=list(scenario_labels.keys()),
        format_func=lambda x: scenario_labels[x],
        label_visibility="collapsed",
    )
    selected_order = orders[selected_of_id]


    st.markdown("---")
    st.markdown(f"**Selected production order: `{selected_order['orderNumber']}`**")
    st.markdown(f"- Product: `{selected_order['productCode']}`  —  Qty: **{selected_order['quantity']}**")


    due_dt = datetime.fromisoformat(selected_order["dueDate"].replace("Z", "+00:00"))
    _days_left = (due_dt - NOW_UTC).days
    _dl_icon, _dl_color = days_remaining_style(_days_left)


    st.markdown(
        f"<div style='text-align:center; padding:12px; border:2px solid {_dl_color}; "
        f"border-radius:10px; margin:8px 0;'>"
        f"<div style='font-size:2em; font-weight:bold; color:{_dl_color};'>"
        f"{_dl_icon} {_days_left} days</div>"
        f"<div>before the customer due date ({selected_order['dueDate'][:10]})</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.caption("Calculation: customer due date minus the simulated current date.")


    st.markdown("---")
    st.markdown("**Component availability for this production order**")
    stock_df = pd.DataFrame([
        {
            "Component": k,
            "Available": v,
            "Required": next(
                (c["qtyPerUnit"] * selected_order["quantity"]
                 for c in selected_order["components"] if c["itemCode"] == k), 0
            )
        }
        for k, v in selected_order["stock"].items()
    ])
    stock_df["Shortage"] = (stock_df["Required"] - stock_df["Available"]).clip(lower=0)
    stock_df["Status"] = stock_df.apply(lambda r: "✅" if r["Available"] >= r["Required"] else "❌", axis=1)
    st.dataframe(stock_df, use_container_width=True, hide_index=True)




with right:


    # ─── Maestro ────────────────────────────────────────────────
    st.markdown("#### 🎼 Maestro — Production flow analysis and blocking risk")


    if st.button("🎼 Run Maestro analysis", key="btn_maestro", type="primary"):
        output = run_maestro(selected_of_id, orders)
        st.session_state["maestro_outputs"][selected_of_id] = output


    # ── Maestro display ───────────────────────────────────
    if selected_of_id in st.session_state["maestro_outputs"]:
        output = st.session_state["maestro_outputs"][selected_of_id]
        risk = output["risk_level"]
        score = output["global_risk_score"]
        action = output["recommended_action"]
        prob = output["probabilite_blocage_pct"]
        delay = output["estimated_delay_days"]
        penalty = output["estimated_penalty_eur"]
        etape = output.get("etape_a_risque")
        days_until_due = output.get("days_until_due", "?")


        risk_icons = {"VERT": "🟢", "ORANGE": "🟠", "ROUGE": "🔴"}
        st.markdown(f"##### {risk_icons.get(risk, '⚪')} Risk level: **{risk}** (score {score}/100)")


        if etape:
            st.info(
                f"📍 **Critical step identified**: {etape['operationId']} ({etape['description']}) — "
                f"reached in about **{etape['time_to_reach_days']} days**. "
                f"Impacted component: **{etape['composant_manquant']}**."
            )


        rc1, rc2, rc3, rc4 = st.columns(4)
        rc1.metric("Blocking probability", f"{prob}%")
        rc2.metric("Estimated delay", f"{delay} d")
        rc3.metric("Estimated penalties", f"{penalty:,.0f} €")
        rc4.metric("Days before due date", f"{days_until_due} d")


        # ──────────────────────────────────────────────────────
        # PRODUCTION FLOW — Explicit and self-explanatory timeline
        # ──────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("##### 🎬 Production flow — Steps, durations, and attention points")
        st.caption(
            "Reading guide: each row represents one routing step. "
            "The duration corresponds to the time of the step. The cumulative value represents the elapsed time since the production order started."
        )


        missing_codes = {mc["itemCode"] for mc in output.get("missing_components", [])}


        # Find supplier ETAs by component
        supplier_etas = {}
        for plan in output.get("supplier_order_plan", []):
            supplier_etas[plan["itemCode"]] = plan["estimated_lead_days"]


        # Calculate offset if DELAYED_LAUNCH
        launch_offset_days = 0
        if action == "LANCER_DECALE" and output.get("recommended_launch_date"):
            try:
                launch_dt = datetime.strptime(output["recommended_launch_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                launch_offset_days = (launch_dt - NOW_UTC).days
            except (ValueError, TypeError):
                launch_offset_days = 1


        for op in ROUTING:
            duration_days = round(op["duration_hours"] / WORK_HOURS_PER_DAY, 1)
            cumul_days = round(op["cumulative_end_hours"] / WORK_HOURS_PER_DAY, 1)
            reach_days = round(op["cumulative_start_hours"] / WORK_HOURS_PER_DAY, 1)


            blocked_items = set(op.get("requiredComponents", [])) & missing_codes
            is_risk_step = etape and op["operationId"] == etape["operationId"]


            # Icon
            if is_risk_step:
                icon = "🔴"
            elif blocked_items:
                icon = "🟠"
            else:
                icon = "🟢"


            header_text = (
                f"{icon} **{op['operationId']}** — {op['description']} "
                f"(step duration: {duration_days}d | cumulative from start: {cumul_days}d)"
            )
            st.markdown(header_text)


            # Warnings for this step
            if blocked_items:
                for item in blocked_items:
                    eta = supplier_etas.get(item)
                    effective_reach = reach_days + launch_offset_days
                    if eta is not None:
                        if eta <= effective_reach:
                            st.markdown(
                                f"&nbsp;&nbsp;&nbsp;&nbsp;✅ {item} — supplier ETA D+{eta}, "
                                f"step reached at D+{effective_reach:.0f} → **the part should be available on time**"
                            )
                        else:
                            st.markdown(
                                f"&nbsp;&nbsp;&nbsp;&nbsp;🔴 **Attention point for {item}** — "
                                f"supplier ETA D+{eta}, step reached at D+{effective_reach:.0f} → "
                                f"**risk of blockage at this step**"
                            )
                    else:
                        st.markdown(
                            f"&nbsp;&nbsp;&nbsp;&nbsp;🟠 {item} missing — no supplier mitigation identified"
                        )


        # Timing summary message
        if etape and output.get("supplier_order_plan"):
            relevant = [p for p in output["supplier_order_plan"]
                        if p["itemCode"] == etape.get("composant_manquant")]
            if relevant:
                eta = relevant[0]["estimated_lead_days"]
                reach = etape["time_to_reach_days"]


                st.markdown("---")
                if action == "LANCER_DECALE":
                    new_reach = reach + launch_offset_days
                    st.info(
                        f"📐 **Timeline reading**: if the production order starts immediately, "
                        f"step {etape['operationId']} will be reached in **{reach} days**. "
                        f"Part ETA: D+{eta} → **actual risk of blockage**.\n\n"
                        f"💡 **Maestro recommendation**: delay the launch by **{launch_offset_days} day(s)**. "
                        f"The critical step would then be reached at D+{new_reach:.0f}, "
                        f"for a part ETA at D+{eta} → **reduced risk**."
                    )
                elif eta > reach:
                    st.error(
                        f"📐 **Timeline reading**: if the production order starts now, "
                        f"step {etape['operationId']} will be reached in **{reach} days**. "
                        f"Part ETA: D+{eta} → **probable blockage if nothing changes**."
                    )
                else:
                    st.success(
                        f"📐 **Timeline reading**: the part is expected at D+{eta}, "
                        f"and step {etape['operationId']} will be reached at D+{reach} → **the flow remains secured**."
                    )


        # ── Maestro recommendation ──
        st.markdown("---")
        st.markdown("##### 💡 Launch recommendation")
        action_labels = {
            "LANCER_IMMEDIAT": ("✅", "Launch immediately"),
            "LANCER_DECALE": ("⚠️", "Delay launch"),
            "REPORTER_ET_REPLANIFIER": ("🛑", "Postpone and reschedule"),
        }
        a_icon, a_label = action_labels.get(action, ("?", action))


        if action == "LANCER_IMMEDIAT":
            st.success(f"{a_icon} **{a_label}** — The risk level remains compatible with the planned launch.")
        elif action == "LANCER_DECALE":
            launch_date = output.get("recommended_launch_date", "?")
            st.warning(
                f"{a_icon} **{a_label}** — Recommended launch on **{launch_date}** "
                f"to better align the production flow with part arrivals."
            )
        else:
            st.error(f"{a_icon} **{a_label}** — The risk is too high; rescheduling is preferable.")


        st.markdown(f"💬 *{output['maestro_message']}*")


        # ──────────────────────────────────────────────────────
        # RESCHEDULING SLOTS (critical scenario)
        # ──────────────────────────────────────────────────────
        opts = output.get("rescheduling_options", [])
        if opts:
            st.markdown("---")
            st.markdown("##### 🔄 Proposed rescheduling slots")
            st.caption("In a critical case, Maestro proposes several launch options with their estimated impact.")


            for i, opt in enumerate(opts):
                with st.expander(f"**Option {i+1}** : {opt['label']}", expanded=(i == 0)):
                    st.markdown(f"- **Proposed launch date** : {opt['launch_date']}")
                    st.markdown(f"- **Estimated PO completion** : {opt['estimated_completion']}")
                    st.markdown(f"- **Estimated customer delay** : +{opt['delay_client_days']} day(s)")
                    st.markdown(f"- **Estimated penalties** : {opt['penalty_eur']:,.0f} €")
                    st.markdown(f"- *{opt['comment']}*")


            # User choice
            resch_key = f"resch_{selected_of_id}"
            if resch_key not in st.session_state.get("rescheduling_choices", {}):
                option_labels = [f"Option {i+1} — {o['label']}" for i, o in enumerate(opts)]
                option_labels.append("Other (keep my current plan)")


                chosen_resch = st.radio(
                    "Your decision:",
                    options=range(len(option_labels)),
                    format_func=lambda x: option_labels[x],
                    key=f"radio_resch_{selected_of_id}",
                )


                if st.button("✅ Confirm slot", key=f"btn_resch_{selected_of_id}"):
                    if chosen_resch < len(opts):
                        msg = apply_rescheduling_choice(
                            selected_of_id, orders, st.session_state["maestro_outputs"], chosen_resch
                        )
                        st.session_state.setdefault("rescheduling_choices", {})[resch_key] = msg
                        st.success(msg)
                        st.rerun()
                    else:
                        st.session_state.setdefault("rescheduling_choices", {})[resch_key] = (
                            "You chose to keep the current schedule. No rescheduling applied."
                        )
                        st.rerun()
            else:
                st.success(f"🎯 {st.session_state['rescheduling_choices'][resch_key]}")


        # ──────────────────────────────────────────────────────
        # SUPPLIER NOTIFICATION — With user validation
        # ──────────────────────────────────────────────────────
        emails = output.get("simulated_emails", [])
        if emails:
            st.markdown("---")
            st.markdown("##### 📧 Draft supplier message")
            st.caption("Maestro prepares the message. The user then chooses whether to send it, edit it, or cancel it.")


            for idx, email in enumerate(emails):
                email_key = f"email_{selected_of_id}_{idx}"


                # Already processed status?
                if email.get("status"):
                    st.markdown(
                        f"**Supplier action** ({email['to_name']}) : "
                        f"{email.get('action_label', email['status'])}"
                    )
                    with st.expander(f"📨 View message — {email['subject']}"):
                        st.markdown(f"**To** : {email['to_name']} <{email['to']}>")
                        st.markdown(f"**Subject** : {email['subject']}")
                        st.divider()
                        st.text(email["body"])
                    continue


                st.markdown(f"📩 **Message prepared for {email['to_name']}** — {email['subject']}")


                btn_col1, btn_col2, btn_col3 = st.columns(3)


                with btn_col1:
                    if st.button("✅ Send", key=f"btn_send_{email_key}"):
                        apply_email_action(output, idx, "envoyer")
                        st.rerun()
                with btn_col2:
                    if st.button("✏️ Edit", key=f"btn_edit_{email_key}"):
                        st.session_state[f"editing_{email_key}"] = True
                        st.rerun()
                with btn_col3:
                    if st.button("❌ Cancel", key=f"btn_cancel_{email_key}"):
                        apply_email_action(output, idx, "annuler")
                        st.rerun()


                # Edit area if "Edit" clicked
                if st.session_state.get(f"editing_{email_key}"):
                    new_body = st.text_area(
                        "Edit the message:",
                        value=email["body"],
                        height=200,
                        key=f"ta_{email_key}",
                    )
                    if st.button("📤 Send edited message", key=f"btn_sendmod_{email_key}"):
                        apply_email_action(output, idx, "modifier", new_body)
                        st.session_state.pop(f"editing_{email_key}", None)
                        st.rerun()


                with st.expander(f"👁️ Message preview"):
                    st.markdown(f"**To** : {email['to_name']} <{email['to']}>")
                    st.markdown(f"**Subject** : {email['subject']}")
                    st.divider()
                    st.text(email["body"])


        # ── Supplier plan ──
        plan = output.get("supplier_order_plan", [])
        if plan:
            with st.expander("📦 Supplier mitigation plan"):
                st.dataframe(pd.DataFrame(plan), use_container_width=True, hide_index=True)


        # ── Technical details ──
        if output.get("reasoning"):
            with st.expander("💬 Detailed explanation of the analysis"):
                st.write(output["reasoning"])
        if output.get("risk_factors"):
            with st.expander("📊 Factors contributing to the risk"):
                st.dataframe(pd.DataFrame(output["risk_factors"]), use_container_width=True, hide_index=True)
        with st.expander("🔧 Technical JSON"):
            st.json(output)


        # ──────────────────────────────────────────────────────
        # OPERATOR DECISION
        # ──────────────────────────────────────────────────────
        st.markdown("---")
        if output.get("operator_decision"):
            op_dec = output["operator_decision"]
            dec_label = action_labels.get(op_dec, ("?", op_dec))[1]
            agreed = "✅ (aligned with Maestro)" if op_dec == action else "⚡ (operator decision differs)"
            st.success(f"🎯 **Final decision: {dec_label}** {agreed}")
            st.markdown(f"**Operational instruction** : {output.get('instruction', '—')}")
        else:
            st.markdown("##### 🎯 Final decision")
            decision_options = ["LANCER_IMMEDIAT", "LANCER_DECALE", "REPORTER_ET_REPLANIFIER"]
            decision_labels = {
                "LANCER_IMMEDIAT": "✅ Launch immediately",
                "LANCER_DECALE": "⚠️ Launch with delay",
                "REPORTER_ET_REPLANIFIER": "🛑 Postpone and reschedule",
            }
            default_idx = decision_options.index(action) if action in decision_options else 0


            chosen = st.radio(
                "Selected action:",
                options=decision_options,
                format_func=lambda x: f"{decision_labels[x]} {'★ Recommended' if x == action else ''}",
                index=default_idx,
                key=f"radio_{selected_of_id}",
                horizontal=True,
            )
            if chosen != action:
                st.warning(f"⚡ You are deviating from Maestro’s initial recommendation ({a_label}).")


            if st.button("✅ Confirm decision", key=f"btn_validate_{selected_of_id}", type="primary"):
                instruction = apply_operator_decision(
                    selected_of_id, orders, st.session_state["maestro_outputs"], chosen
                )
                st.success(f"🎯 **Decision confirmed: {decision_labels[chosen]}**")
                st.markdown(f"**Operational instruction** : {instruction}")
                st.rerun()




# =============================================================================
# Sentinelle watchlist — Dynamic KPIs
# =============================================================================



st.divider()
st.subheader("🔗 Orchestrator — Production orders to place under monitoring")


# ── Orchestrator ──
st.markdown("#### Feed the Sentinelle watchlist")


if st.button("Update watchlist", key="btn_orch"):
    m_outputs = st.session_state["maestro_outputs"]
    if not m_outputs:
        st.warning("Run Maestro on at least one production order first.")
    else:
        watchlist = run_orchestrator(m_outputs, orders)
        st.session_state["watchlist"] = watchlist
        if watchlist:
            st.success(f"✅ {len(watchlist)} production order(s) require material monitoring")
        else:
            st.info("No production orders to monitor — no particular attention needed at this stage.")


# Display the watchlist with dynamic status
watchlist = st.session_state["watchlist"]
if watchlist:
    st.markdown("**Sentinelle watchlist** — Currently monitored production orders")
    wl_rows = []
    for w in watchlist:
        of_id = w["of_id"]
        s = sentinelle_outs.get(of_id, {})
        sim_day = orders.get(of_id, {}).get("simulated_days", 0)


        # Current status — Sentinelle alone decides
        if s.get("warning_status") == "LEVE":
            status_label = "✅ Risk cleared"
        elif s.get("warning_status") == "CONFIRME":
            status_label = "🔴 Risk confirmed"
        elif s.get("warning_status") == "EN_SURVEILLANCE":
            status_label = "🔍 Active monitoring"
        else:
            status_label = "🔍 Awaiting Sentinelle check"


        wl_rows.append({
            "Production order": orders.get(of_id, {}).get("orderNumber", of_id),
            "Initial risk": w.get("risk_level", "?"),
            "Current status": status_label,
            "Simulated day": f"D+{sim_day}",
            "Critical step": w.get("etape_a_risque", "—"),
            "Days remaining": w.get("days_until_due", "?"),
        })
    st.dataframe(pd.DataFrame(wl_rows), use_container_width=True, hide_index=True)


_is_medium_scenario = selected_order.get("scenario") == "Medium"

if _is_medium_scenario:
    st.divider()
    st.subheader("⏩ Move time and the production flow forward")
    st.caption(
        "This simulation moves production forward in time. "
        "It does not confirm part arrivals: only **Sentinelle** can do that during its check."
    )


if _is_medium_scenario and selected_of_id in st.session_state["maestro_outputs"]:
    m_out = st.session_state["maestro_outputs"][selected_of_id]


    # Current simulated day
    current_sim_day = selected_order.get("simulated_days", 0)
    st.markdown(f"📅 **Current simulated day: D+{current_sim_day}**")


    # Advance buttons
    sim_col1, sim_col2, sim_col3 = st.columns(3)


    with sim_col1:
        if st.button("⏩ +1 day", key=f"btn_sim_1_{selected_of_id}", type="primary"):
            result = advance_time(
                selected_of_id, orders, st.session_state["maestro_outputs"], days=1
            )
            st.session_state["time_sim_results"][selected_of_id] = result
            st.rerun()


    with sim_col2:
        if st.button("⏩ +2 days", key=f"btn_sim_2_{selected_of_id}"):
            result = advance_time(
                selected_of_id, orders, st.session_state["maestro_outputs"], days=2
            )
            st.session_state["time_sim_results"][selected_of_id] = result
            st.rerun()


    with sim_col3:
        if st.button("⏩ +3 days", key=f"btn_sim_3_{selected_of_id}"):
            result = advance_time(
                selected_of_id, orders, st.session_state["maestro_outputs"], days=3
            )
            st.session_state["time_sim_results"][selected_of_id] = result
            st.rerun()


    # Display simulation results
    sim_result = st.session_state["time_sim_results"].get(selected_of_id)
    if sim_result:
        st.markdown("---")
        st.markdown(f"##### Projection of the production order at D+{sim_result['days_advanced']}")


        # Contextual message
        if sim_result.get("blocked"):
            st.error(f"🔴 {sim_result['message']}")
        elif sim_result.get("days_remaining_to_risk") is not None and sim_result["days_remaining_to_risk"] <= 1:
            st.warning(f"🟠 {sim_result['message']}")
        elif sim_result.get("missing_components"):
            st.warning(f"🟠 {sim_result['message']}")
        else:
            st.success(f"🟢 {sim_result['message']}")


        # Timeline update
        st.markdown("**Production flow progress**")
        sim_cols = st.columns(len(ROUTING))
        hours = sim_result["hours_elapsed"]
        for i, (col, op) in enumerate(zip(sim_cols, ROUTING)):
            if hours >= op["cumulative_end_hours"]:
                col.markdown(f"✅ **{op['operationId'][:4]}**")
                col.caption("Step completed")
            elif hours >= op["cumulative_start_hours"]:
                col.markdown(f"🟠 **{op['operationId'][:4]}**")
                col.caption("Step in progress")
            else:
                if sim_result.get("blocked") and sim_result["blocked_at"] and op["operationId"] == sim_result["blocked_at"]["operationId"]:
                    col.markdown(f"🔴 **{op['operationId'][:4]}**")
                    col.caption("Blocking point reached")
                else:
                    col.markdown(f"⚪ {op['operationId'][:4]}")
                    col.caption("Upcoming")


        # Waiting parts (information only, no stock change)
        if sim_result.get("waiting_parts"):
            st.markdown("**⏳ Expected components**")
            for p in sim_result["waiting_parts"]:
                if p["days_remaining"] > 0:
                    st.markdown(
                        f"- ⏳ **{p['itemCode']}** × {p['qty_ordered']} (supplier {p['supplier']}, "
                        f"ETA D+{p['eta_days']}, {p['days_remaining']} day(s) remaining)"
                    )
                else:
                    st.markdown(
                        f"- 📦 **{p['itemCode']}** × {p['qty_ordered']} (supplier {p['supplier']}, "
                        f"ETA D+{p['eta_days']} — theoretical arrival date reached, **run Sentinelle to verify**)"
                    )


        # Risk proximity
        if sim_result.get("blocked") and m_out.get("rescheduling_options"):
            st.markdown("---")
            st.warning(
                "🔄 **The critical point has been reached** — run Sentinelle to confirm whether the parts are available. "
                "If the blockage is confirmed, Maestro has prepared rescheduling options:"
            )
            for opt in m_out["rescheduling_options"]:
                st.markdown(
                    f"- **{opt['label']}** — customer delay +{opt['delay_client_days']}d, "
                    f"penalties {opt['penalty_eur']:,.0f}€ — *{opt['comment']}*"
                )


elif _is_medium_scenario:
    st.info("Run Maestro on this production order first to enable time simulation.")




# =============================================================================
# Sentinelle — Ground truth agent: checks parts at current simulated date
# =============================================================================



st.divider()
st.markdown("#### 🔭 Sentinelle — Ground truth check at current date")
st.caption(
    "Sentinelle is the ground truth agent. It checks, on the current simulated day, "
    "whether the critical components have actually arrived, then decides whether the alert "
    "should remain active or be cleared. It does not predict risk — it **verifies** it."
)


watchlist = st.session_state["watchlist"]
if watchlist:
    # Scenario-specific guidance
    medium_ofs = [w for w in watchlist if orders.get(w["of_id"], {}).get("scenario") == "Medium"]
    critical_ofs = [w for w in watchlist if orders.get(w["of_id"], {}).get("scenario") == "Critical"]
    if medium_ofs:
        st.info("💡 **Medium** scenario — Advance time first so parts can arrive, then run Sentinelle to confirm delivery.")
    if critical_ofs:
        st.warning("💡 **Critical** scenario — Run Sentinelle directly to confirm the risk (no time advance needed).")

    # Stock preview — what Sentinelle can observe on the current simulated date
    previews = get_stock_updates_preview(orders, st.session_state["maestro_outputs"], watchlist)
    for prev in previews:
        of_label = prev["orderNumber"]
        sim_day = orders.get(prev["of_id"], {}).get("simulated_days", 0)
        if prev["has_arrivals"]:
            arr_rows = [a for a in prev["arrivals"] if a["delta"] > 0]
            if arr_rows:
                st.success(f"📦 **{of_label}** (D+{sim_day}) — Items pending confirmation:")
                st.dataframe(
                    pd.DataFrame(arr_rows)[["itemCode", "stock_before", "stock_after", "delta", "type"]],
                    use_container_width=True, hide_index=True,
                )
            wait_rows = [a for a in prev["arrivals"] if a["delta"] == 0]
            if wait_rows:
                st.info(f"⏳ **{of_label}** — Still no confirmed receipt:")
                st.dataframe(
                    pd.DataFrame(wait_rows)[["itemCode", "stock_before", "type"]],
                    use_container_width=True, hide_index=True,
                )
        else:
            st.info(f"📭 **{of_label}** (D+{sim_day}) — No arrival recorded on this date.")


    if st.button("🔭 Run Sentinelle", key="btn_sentinelle", type="primary"):
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
                    f"✅ **{orders[of_id]['orderNumber']}** — Risk cleared {ev_icons.get(evolution, '')} "
                    f"{res['initial_risk_level']} → {res['current_risk_level']}"
                )
            elif warning == "CONFIRME":
                st.error(
                    f"🔴 **{orders[of_id]['orderNumber']}** — Risk confirmed {ev_icons.get(evolution, '')} "
                    f"Estimated delay: +{res.get('updated_delay_days', '?')} days"
                )
            else:
                st.warning(
                    f"🔍 **{orders[of_id]['orderNumber']}** — Monitoring maintained "
                    f"{ev_icons.get(evolution, '')}"
                )


            st.markdown(f"💬 *{res['sentinelle_message']}*")


            if res.get("parts_tracking"):
                with st.expander(f"📦 Component tracking — {orders[of_id]['orderNumber']}"):
                    st.dataframe(pd.DataFrame(res["parts_tracking"]), use_container_width=True, hide_index=True)


            if res.get("plan_b_needed") and res.get("rescheduling_proposal"):
                prop = res["rescheduling_proposal"]
                st.warning(
                    f"🔄 **Rescheduling option** : {prop['label']} — "
                    f"customer delay +{prop['delay_client_days']}d, penalties {prop['penalty_eur']:,.0f}€"
                )


            st.markdown(f"**Operational instruction** : {res['instruction']}")


        # Recalculate the watchlist after each Sentinelle run
        st.session_state["watchlist"] = refresh_watchlist(orders, watchlist)
        st.rerun()


else:
    st.caption("Activate the orchestrator first to populate the monitoring watchlist.")




# =============================================================================
# Resume production (Plan B — critical scenario only)
# =============================================================================



st.divider()
st.markdown("#### ▶️ Plan B — Resume after confirmed blockage")
st.caption(
    "This section is reserved for critical cases where, despite anticipation, "
    "production has actually been interrupted. "
    "In the nominal scenario, the goal of the product is precisely to avoid getting to this point."
)



# Only blocked production orders (critical scenario), not those where risk was just cleared
ready_ofs = {
    of_id: o for of_id, o in sim_orders.items()
    if o["status"] == "Bloqué" or (o["status"] == "RisqueLeve" and o.get("scenario") == "Critique")
}
if ready_ofs:
    for of_id, order in ready_ofs.items():
        col_btn, col_info = st.columns([1, 3])
        with col_btn:
            if st.button(f"▶️ Resume {order['orderNumber']}", key=f"btn_resume_{of_id}"):
                resume_of(of_id, orders)
                st.session_state["watchlist"] = [
                    w for w in st.session_state["watchlist"] if w["of_id"] != of_id
                ]
                st.success(f"✅ **{order['orderNumber']}** → **Production order relaunched**")
                st.rerun()
        with col_info:
            st.markdown(f"Current status: {order['status']} — Conditions to resume have been met")
else:
    st.caption("No production order is currently in an exceptional restart case.")




# =============================================================================
# Production order focus — Maestro & Sentinelle messages
# =============================================================================



st.divider()
st.subheader("🔎 Production order focus — History and consolidated view")



focus_options = {of_id: o["orderNumber"] for of_id, o in sim_orders.items()}
focus_of_id = st.selectbox(
    "Select a production order:",
    options=list(focus_options.keys()),
    format_func=lambda x: focus_options[x],
    key="focus_of",
)



focus_order = orders[focus_of_id]
m_out = st.session_state["maestro_outputs"].get(focus_of_id, {})
s_out = st.session_state["sentinelle_outputs"].get(focus_of_id, {})
ts_out = st.session_state["time_sim_results"].get(focus_of_id, {})



# Timeline progression — adapted per scenario
st.markdown("**Demo case progression**")
has_decision = bool(m_out.get("operator_decision"))
has_sim = bool(ts_out)
focus_scenario = focus_order.get("scenario", "")

# Steps and progress depend on the scenario
if focus_scenario == "OK":
    # OK: no monitoring needed
    steps = ["PO creation", "Maestro analysis", "Decision", "Closure"]
    if focus_order["status"] in ("Released",):
        current_step = 3
    elif has_decision:
        current_step = 2
    elif m_out:
        current_step = 1
    else:
        current_step = 0
elif focus_scenario == "Medium":
    # Medium: time advance then Sentinelle verifies
    steps = ["PO creation", "Maestro analysis", "Decision", "Time advance", "Sentinelle check", "Closure"]
    if focus_order["status"] in ("Released",):
        current_step = 5
    elif s_out:
        current_step = 4
    elif has_sim:
        current_step = 3
    elif has_decision:
        current_step = 2
    elif m_out:
        current_step = 1
    else:
        current_step = 0
else:
    # Critical: Sentinelle confirms risk directly (no time advance)
    steps = ["PO creation", "Maestro analysis", "Decision", "Sentinelle check", "Closure"]
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



cols_tl = st.columns(len(steps))
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
    st.markdown("**🎼 Maestro reading**")
    if m_out:
        risk = m_out["risk_level"]
        risk_icon = {"VERT": "🟢", "ORANGE": "🟠", "ROUGE": "🔴"}.get(risk, "⚪")
        st.markdown(f"{risk_icon} Risk **{risk}** — Score {m_out['global_risk_score']}/100")
        st.markdown(f"*{m_out['maestro_message']}*")
        if m_out.get("operator_decision"):
            dec_labels = {
                "LANCER_IMMEDIAT": "Launch immediately",
                "LANCER_DECALE": "Delay launch",
                "REPORTER_ET_REPLANIFIER": "Postpone and reschedule",
            }
            st.markdown(f"🎯 **Selected decision: {dec_labels.get(m_out['operator_decision'], m_out['operator_decision'])}**")
    else:
        st.caption("No Maestro analysis available for this production order.")



with col_s:
    st.markdown("**🔭 Sentinelle reading / Simulated time**")
    sim_day = focus_order.get("simulated_days", 0)
    if s_out:
        w = s_out["warning_status"]
        w_icons = {"LEVE": "✅", "CONFIRME": "🔴", "EN_SURVEILLANCE": "🔍"}
        st.markdown(f"{w_icons.get(w, '?')} Alert **{w}** — {s_out['initial_risk_level']} → {s_out['current_risk_level']}")
        st.markdown(f"*{s_out['sentinelle_message']}*")
    if ts_out:
        st.markdown(f"📅 Simulated time: **D+{ts_out['days_advanced']}** — {ts_out['message']}")
    if not s_out and not ts_out:
        st.caption("No Sentinelle monitoring or time progression recorded for this production order.")
