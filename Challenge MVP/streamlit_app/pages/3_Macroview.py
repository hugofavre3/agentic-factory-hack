"""
Page 3 — Macro View: Impact of Maestro & Sentinelle decisions


Portfolio / shop-floor view.
This page gives a consolidated reading of the impact of decisions:
- overall risk level on production orders,
- buffer before customer due dates,
- comparison with / without AI-driven control,
- dynamic watchlist,
- overall shop-floor health.
"""


import streamlit as st
import pandas as pd
import sys, os
from datetime import datetime, timezone, date



sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data import build_seed_orders, ROUTING, WORK_HOURS_PER_DAY



st.set_page_config(page_title="Macro View — AI Impact", page_icon="📊", layout="wide")



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
maestro_outs = st.session_state["maestro_outputs"]
sentinelle_outs = st.session_state["sentinelle_outputs"]
time_sim = st.session_state["time_sim_results"]



def days_remaining_style(days_left):
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
    f"<span style='font-size:1.3em; color:white;'>📅 Today’s date: <b>{TODAY.strftime('%d/%m/%Y')}</b></span>"
    f"</div>",
    unsafe_allow_html=True,
)



st.title("📊 Macro View: Impact of Maestro & Sentinelle decisions")
st.caption(
    "This view provides a consolidated reading of the production order portfolio: "
    "where the tensions are, which delays can be avoided, "
    "and to what extent the shop floor remains under control thanks to anticipation and monitoring."
)



st.divider()



# =============================================================================
# KPIs — Remaining days + methodology
# =============================================================================



total_of = len(sim_orders)
of_analysed = sum(1 for k in sim_orders if k in maestro_outs)



# Remaining days per production order
days_by_of = {}
for of_id, order in sim_orders.items():
    due_dt = datetime.fromisoformat(order["dueDate"].replace("Z", "+00:00"))
    days_by_of[of_id] = (due_dt - NOW_UTC).days



worst_of_id = min(days_by_of, key=days_by_of.get) if days_by_of else None
worst_days = days_by_of.get(worst_of_id, 99)
worst_icon, worst_color = days_remaining_style(worst_days)



# Delay calculations with/without AI
delay_sans_ia_total = 0
delay_avec_ia_total = 0
penalties_sans_ia = 0
penalties_avec_ia = 0



for of_id, order in sim_orders.items():
    m = maestro_outs.get(of_id, {})
    s = sentinelle_outs.get(of_id, {})
    ts = time_sim.get(of_id, {})


    delay_sans_ia = m.get("estimated_delay_days", 0)
    delay_sans_ia_total += delay_sans_ia
    penalties_sans_ia += m.get("estimated_penalty_eur", 0)


    # With AI: only Sentinelle can clear the risk
    if s.get("warning_status") == "LEVE":
        delay_avec_ia_total += 0
        penalties_avec_ia += 0
    elif s:
        delay_avec_ia_total += s.get("updated_delay_days", 0)
        penalties_avec_ia += s.get("updated_delay_days", 0) * 5000
    elif m.get("recommended_action") == "LANCER_IMMEDIAT":
        delay_avec_ia_total += 0
    else:
        delay_avec_ia_total += m.get("estimated_delay_days", 0)



delay_evite = max(0, delay_sans_ia_total - delay_avec_ia_total)
penalties_evitees = max(0, penalties_sans_ia - penalties_avec_ia)



of_risk_leve = sum(
    1 for of_id in sim_orders
    if sentinelle_outs.get(of_id, {}).get("warning_status") == "LEVE"
)


of_at_risk = sum(
    1 for of_id in sim_orders
    if maestro_outs.get(of_id, {}).get("risk_level") in ("ORANGE", "ROUGE")
    and sentinelle_outs.get(of_id, {}).get("warning_status") != "LEVE"
)



# ── KPI display ──
kpi_cols = st.columns(5)



with kpi_cols[0]:
    st.markdown(
        f"<div style='text-align:center; padding:16px; border:3px solid {worst_color}; "
        f"border-radius:12px; background:{worst_color}22;'>"
        f"<div style='font-size:2.5em; font-weight:bold; color:{worst_color};'>"
        f"{worst_icon} {worst_days} d</div>"
        f"<div style='font-size:0.9em;'>Lowest remaining buffer</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.caption("Method: minimum number of days remaining before customer due date across all production orders.")


with kpi_cols[1]:
    st.metric(
        "Production orders analysed",
        f"{of_analysed}/{total_of}",
    )
    st.caption("Method: number of production orders already analysed by Maestro.")


with kpi_cols[2]:
    st.metric(
        "⏱️ Estimated delay avoided",
        f"−{delay_evite} d" if delay_evite > 0 else "0 d",
    )
    st.caption("Method: cumulative delay without AI control minus cumulative delay with AI control.")


with kpi_cols[3]:
    st.metric(
        "💰 Penalties avoided",
        f"{penalties_evitees:,.0f} €" if penalties_evitees > 0 else "—",
    )
    st.caption("Method: projected penalties without AI minus projected penalties with AI.")


with kpi_cols[4]:
    st.metric(
        "✅ Risks cleared",
        f"{of_risk_leve}",
    )
    st.caption("Method: production orders whose alert has been cleared by Sentinelle.")




# =============================================================================
# Remaining days per production order — detailed view
# =============================================================================



st.divider()
st.subheader("📅 Buffer before due date by production order")
st.caption("Reading: 🟢 comfortable buffer | 🟠 needs attention | 🔴 very low buffer")



days_rows = []
for of_id, order in sim_orders.items():
    dl = days_by_of[of_id]
    dl_icon, dl_color = days_remaining_style(dl)


    # Current risk
    ts = time_sim.get(of_id, {})
    s = sentinelle_outs.get(of_id, {})
    m = maestro_outs.get(of_id, {})


    if ts.get("warning_status") == "LEVE" or s.get("warning_status") == "LEVE":
        risk_label = "🟢 Risk cleared"
    elif ts.get("warning_status") == "CONFIRME" or s.get("warning_status") == "CONFIRME":
        risk_label = "🔴 Risk confirmed"
    elif m.get("risk_level"):
        risk_icons = {"VERT": "🟢", "ORANGE": "🟠", "ROUGE": "🔴"}
        risk_label = f"{risk_icons.get(m['risk_level'], '⚪')} {m['risk_level']}"
    else:
        risk_label = "⚪ Not analysed"


    days_rows.append({
        "PO": order["orderNumber"],
        "Due date": order["dueDate"][:10],
        f"{dl_icon} Days remaining": dl,
        "Risk": risk_label,
        "Status": order.get("status", "—"),
    })



st.dataframe(pd.DataFrame(days_rows), use_container_width=True, hide_index=True)




# =============================================================================
# Compared timeline — With vs Without AI
# =============================================================================



st.divider()
st.subheader("📈 Macro comparison — With AI control vs without AI")



if not maestro_outs:
    st.info("Run Maestro from the Cockpit to feed this comparison.")
else:
    timeline_rows = []
    for of_id, order in sim_orders.items():
        m = maestro_outs.get(of_id, {})
        s = sentinelle_outs.get(of_id, {})
        ts = time_sim.get(of_id, {})
        if not m:
            continue


        due_date = order["dueDate"][:10]


        # Without AI
        delay_sans = m.get("estimated_delay_days", 0)
        end_sans = f"+{delay_sans}d delay" if delay_sans > 0 else "On time"


        # With AI
        if ts.get("warning_status") == "LEVE" or s.get("warning_status") == "LEVE":
            delay_avec = 0
            end_avec = "✅ On time (risk cleared)"
        elif s:
            delay_avec = s.get("updated_delay_days", 0)
            end_avec = f"+{delay_avec}d delay" if delay_avec > 0 else "✅ On time"
        elif m.get("recommended_action") == "LANCER_IMMEDIAT":
            delay_avec = 0
            end_avec = "✅ On time"
        else:
            delay_avec = delay_sans
            end_avec = f"+{delay_avec}d" if delay_avec > 0 else "—"


        retard_evite_of = max(0, delay_sans - delay_avec)


        timeline_rows.append({
            "PO": order["orderNumber"],
            "Due date": due_date,
            "Without AI control": end_sans,
            "With AI control": end_avec,
            "Delay avoided": f"{retard_evite_of}d" if retard_evite_of > 0 else "—",
        })


    if timeline_rows:
        st.dataframe(pd.DataFrame(timeline_rows), use_container_width=True, hide_index=True)


    # Bar chart
    st.markdown("**Estimated delay per production order: direct comparison**")
    chart_rows = []
    for of_id, order in sim_orders.items():
        m = maestro_outs.get(of_id, {})
        s = sentinelle_outs.get(of_id, {})
        ts = time_sim.get(of_id, {})
        if not m:
            continue


        delay_sans = m.get("estimated_delay_days", 0)
        if ts.get("warning_status") == "LEVE" or s.get("warning_status") == "LEVE":
            delay_avec = 0
        elif s:
            delay_avec = s.get("updated_delay_days", 0)
        else:
            delay_avec = 0 if m.get("recommended_action") == "LANCER_IMMEDIAT" else delay_sans


        chart_rows.append({
            "PO": order["orderNumber"],
            "Without AI (days late)": delay_sans,
            "With AI (days late)": delay_avec,
        })


    if chart_rows:
        st.bar_chart(pd.DataFrame(chart_rows).set_index("PO"))




# =============================================================================
# Decisions table
# =============================================================================



st.divider()
st.subheader("📋 Decisions taken and expected effects")
st.caption("The AI recommends, the operator arbitrates, and Sentinelle then confirms how the risk actually evolves.")



if not maestro_outs:
    st.info("No analysis available.")
else:
    dec_rows = []
    for of_id, order in sim_orders.items():
        m = maestro_outs.get(of_id, {})
        s = sentinelle_outs.get(of_id, {})
        ts = time_sim.get(of_id, {})
        if not m:
            continue


        action_labels = {
            "LANCER_IMMEDIAT": "✅ Launch",
            "LANCER_DECALE": "⚠️ Delay launch",
            "REPORTER_ET_REPLANIFIER": "🛑 Postpone & reschedule",
        }


        # Suppliers
        suppliers = [f"{sp['supplier_name']} ({sp['itemCode']})" for sp in m.get("supplier_order_plan", [])]
        supplier_str = ", ".join(suppliers) if suppliers else "—"


        # Emails
        emails = m.get("simulated_emails", [])
        email_statuses = []
        for e in emails:
            s_label = e.get("action_label", "⏳ Pending")
            email_statuses.append(f"{e.get('to_name', '?')}: {s_label}")
        email_str = " | ".join(email_statuses) if email_statuses else "—"


        # Final delay
        delay = m.get("estimated_delay_days", 0)
        if ts.get("warning_status") == "LEVE" or s.get("warning_status") == "LEVE":
            delay = 0


        # Sentinelle / simulation status
        if ts.get("warning_status") == "LEVE":
            sent_status = "✅ Risk cleared (sim)"
        elif ts.get("warning_status") == "CONFIRME":
            sent_status = "🔴 Confirmed (sim)"
        elif s.get("warning_status") == "LEVE":
            sent_status = "✅ Risk cleared"
        elif s.get("warning_status") == "CONFIRME":
            sent_status = "🔴 Confirmed"
        elif s.get("warning_status"):
            sent_status = "🔍 Under monitoring"
        else:
            sent_status = "—"


        # Chosen rescheduling
        resch = m.get("chosen_rescheduling")
        resch_str = resch["label"] if resch else "—"


        dec_rows.append({
            "PO": order["orderNumber"],
            "Maestro recommendation": action_labels.get(m.get("recommended_action"), "—"),
            "Operator decision": action_labels.get(m.get("operator_decision"), "⏳"),
            "Supplier securing": supplier_str,
            "Email actions": email_str,
            "Rescheduling": resch_str,
            "Final delay": f"+{delay}d" if delay > 0 else "None",
            "Sentinelle status": sent_status,
        })


    if dec_rows:
        st.dataframe(pd.DataFrame(dec_rows), use_container_width=True, hide_index=True)


    st.caption(
        "💡 *The AI recommendation remains a decision aid: final validation stays with the operator.*"
    )




# =============================================================================
# Status distribution
# =============================================================================



st.divider()
st.subheader("📈 Overall shop-floor health")



col_g1, col_g2 = st.columns(2)



with col_g1:
    st.markdown("**Risk level distribution**")
    risk_counts = {"VERT": 0, "ORANGE": 0, "ROUGE": 0, "Not analysed": 0}
    for of_id in sim_orders:
        m = maestro_outs.get(of_id, {})
        ts = time_sim.get(of_id, {})
        s = sentinelle_outs.get(of_id, {})


        if ts.get("warning_status") == "LEVE" or s.get("warning_status") == "LEVE":
            risk_counts["VERT"] += 1
        elif m.get("risk_level") in risk_counts:
            risk_counts[m["risk_level"]] += 1
        else:
            risk_counts["Not analysed"] += 1


    risk_df = pd.DataFrame([
        {"Risk": "🟢 VERT", "Count": risk_counts["VERT"]},
        {"Risk": "🟠 ORANGE", "Count": risk_counts["ORANGE"]},
        {"Risk": "🔴 ROUGE", "Count": risk_counts["ROUGE"]},
        {"Risk": "⚪ Not analysed", "Count": risk_counts["Not analysed"]},
    ])
    risk_df = risk_df[risk_df["Count"] > 0]
    if not risk_df.empty:
        st.bar_chart(risk_df.set_index("Risk"))



with col_g2:
    st.markdown("**Sentinelle monitoring status**")
    sent_counts = {"Risk cleared": 0, "Risk confirmed": 0, "Under monitoring": 0, "Not monitored": 0}
    for of_id in sim_orders:
        ts = time_sim.get(of_id, {})
        s = sentinelle_outs.get(of_id, {})


        if ts.get("warning_status") == "LEVE" or s.get("warning_status") == "LEVE":
            sent_counts["Risk cleared"] += 1
        elif ts.get("warning_status") == "CONFIRME" or s.get("warning_status") == "CONFIRME":
            sent_counts["Risk confirmed"] += 1
        elif ts or s:
            sent_counts["Under monitoring"] += 1
        else:
            sent_counts["Not monitored"] += 1


    sent_df = pd.DataFrame([
        {"Status": "✅ Risk cleared", "Count": sent_counts["Risk cleared"]},
        {"Status": "🔴 Risk confirmed", "Count": sent_counts["Risk confirmed"]},
        {"Status": "🔍 Under monitoring", "Count": sent_counts["Under monitoring"]},
        {"Status": "— Not monitored", "Count": sent_counts["Not monitored"]},
    ])
    sent_df = sent_df[sent_df["Count"] > 0]
    if not sent_df.empty:
        st.bar_chart(sent_df.set_index("Status"))




# =============================================================================
# Added value
# =============================================================================



st.divider()



val1, val2, val3 = st.columns(3)
val1.markdown(
    "### 🎼 Maestro anticipates\n\n"
    "Before any launch, Maestro evaluates whether production is likely "
    "to reach a critical step before the components arrive. "
    "This avoids unsecured starts."
)
val2.markdown(
    "### 🔭 Sentinelle confirms\n\n"
    "Sentinelle tracks production orders under monitoring, checks part arrivals "
    "and updates the risk level. When a risk is cleared, "
    "the watchlist and indicators are refreshed."
)
val3.markdown(
    "### 👤 Humans arbitrate\n\n"
    "The AI prepares the analysis and options, but the final decision remains human. "
    "Recovery after a blockage becomes an exception case; "
    "the primary goal remains anticipation."
)




# =============================================================================
# Summary
# =============================================================================



st.divider()
st.subheader("📝 Synthetic reading of the situation")



if not maestro_outs:
    st.markdown("🔵 **No production order has been analysed yet.** Run Maestro from the Cockpit.")
else:
    lines = []
    of_vert = sum(
        1 for k in sim_orders
        if maestro_outs.get(k, {}).get("risk_level") == "VERT"
        or time_sim.get(k, {}).get("warning_status") == "LEVE"
        or sentinelle_outs.get(k, {}).get("warning_status") == "LEVE"
    )
    of_orange = sum(
        1 for k in sim_orders
        if maestro_outs.get(k, {}).get("risk_level") == "ORANGE"
        and time_sim.get(k, {}).get("warning_status") != "LEVE"
        and sentinelle_outs.get(k, {}).get("warning_status") != "LEVE"
    )
    of_rouge = sum(
        1 for k in sim_orders
        if maestro_outs.get(k, {}).get("risk_level") == "ROUGE"
        and time_sim.get(k, {}).get("warning_status") != "LEVE"
        and sentinelle_outs.get(k, {}).get("warning_status") != "LEVE"
    )


    if of_vert:
        lines.append(f"🟢 **{of_vert}** production order(s) under control")
    if of_orange:
        lines.append(f"🟠 **{of_orange}** production order(s) under watch")
    if of_rouge:
        lines.append(f"🔴 **{of_rouge}** production order(s) at high risk")
    if of_risk_leve:
        lines.append(f"✅ **{of_risk_leve}** risk(s) already cleared")
    if delay_evite > 0:
        lines.append(f"⏱️ **{delay_evite} days** of estimated delays avoided")
    if penalties_evitees > 0:
        lines.append(f"💰 **{penalties_evitees:,.0f} €** of estimated penalties avoided")


    st.markdown("\n\n".join(lines) if lines else "Insufficient data to provide a consolidated reading.")
