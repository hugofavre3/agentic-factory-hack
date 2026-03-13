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



TODAY = date(2026, 3, 13)
NOW_UTC = datetime(2026, 3, 13, tzinfo=timezone.utc)



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
