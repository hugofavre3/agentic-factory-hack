#!/usr/bin/env python3
"""Maestro -- Intelligent Work-Order planning agent.

Analyses each Work Order (OF) and produces a launch/reschedule recommendation:
  * Blocking-risk analysis (BOM vs stock vs routing steps)
  * Risk scoring (0-100) with risk level (VERT / ORANGE / ROUGE)
  * 3-way action: LANCER_IMMEDIAT / LANCER_DECALE / REPORTER_ET_REPLANIFIER
  * Machine-slot recommendation
  * Supplier order plan + simulated emails
  * Rescheduling options (when risk is critical)

Output JSON is consumed by the Orchestrator and the Streamlit dashboards.
Fallback: if Azure AI is not configured the agent runs in pure deterministic mode.

Usage:
    python agents/of_planning_agent_ia.py [--data-dir DATA_DIR] [--output PATH]
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv(override=True)

logger = logging.getLogger(__name__)

WORK_HOURS_PER_DAY = 8


# =============================================================================
# Data loading
# =============================================================================

def load_json(filepath: str) -> Any:
    with open(filepath, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def load_of(data_dir: str) -> Dict:
    of = load_json(os.path.join(data_dir, "of.json"))
    print(f"   OF loaded: {of['id']} -- product {of['productCode']} x {of['quantity']}")
    return of


def load_bom_and_routing(data_dir: str, product_code: str):
    bom = load_json(os.path.join(data_dir, "bom.json"))
    routing = load_json(os.path.join(data_dir, "routing.json"))
    if bom["productCode"] != product_code:
        raise ValueError(f"BOM productCode ({bom['productCode']}) != OF ({product_code})")
    if routing["productCode"] != product_code:
        raise ValueError(f"Routing productCode ({routing['productCode']}) != OF ({product_code})")
    components = bom["components"]
    operations = sorted(routing["operations"], key=lambda op: op["sequence"])
    print(f"   BOM loaded: {len(components)} components")
    print(f"   Routing loaded: {len(operations)} operations")
    return components, operations


def load_stock(data_dir: str) -> Dict[str, int]:
    snapshot = load_json(os.path.join(data_dir, "stock_snapshot.json"))
    stock = {item["itemCode"]: item["qtyAvailable"] for item in snapshot["items"]}
    print(f"   Stock loaded: {len(stock)} references")
    return stock


def load_optional_json(data_dir: str, filename: str) -> Any:
    path = os.path.join(data_dir, filename)
    if os.path.exists(path):
        return load_json(path)
    print(f"   [info] {filename} not found -- optional data skipped")
    return None


# =============================================================================
# Deterministic (MVP) logic
# =============================================================================

def check_availability(components, of_qty, stock):
    missing = []
    for comp in components:
        qty_needed = comp["qtyPerUnit"] * of_qty
        qty_available = stock.get(comp["itemCode"], 0)
        if qty_available < qty_needed:
            missing.append({
                "itemCode": comp["itemCode"],
                "description": comp.get("description", ""),
                "qtyNeeded": qty_needed,
                "qtyAvailable": qty_available,
                "qtyShortage": qty_needed - qty_available,
                "isCritical": comp.get("isCritical", False),
            })
    return missing


def find_cutoff_operation(operations, missing_components):
    missing_codes = {mc["itemCode"] for mc in missing_components}
    for op in operations:
        if set(op.get("requiredComponents", [])) & missing_codes:
            return op
    return None


def find_last_doable_operation(operations, cutoff_op):
    if cutoff_op is None:
        return None
    cutoff_seq = cutoff_op["sequence"]
    doable = [op for op in operations if op["sequence"] < cutoff_seq]
    return doable[-1] if doable else None


def find_risk_steps(operations, missing_components):
    risk_steps = []
    missing_codes = {mc["itemCode"] for mc in missing_components}
    for op in operations:
        blocked_items = set(op.get("requiredComponents", [])) & missing_codes
        for item in blocked_items:
            mc = next(m for m in missing_components if m["itemCode"] == item)
            cum_hours = op.get("cumulative_start_hours", 0)
            risk_steps.append({
                "itemCode": item,
                "operationId": op["operationId"],
                "sequence": op["sequence"],
                "description": op["description"],
                "time_to_reach_hours": cum_hours,
                "time_to_reach_days": round(cum_hours / WORK_HOURS_PER_DAY, 1),
                "qtyShortage": mc["qtyShortage"],
                "isCritical": mc.get("isCritical", False),
            })
    return risk_steps


def find_best_supplier(suppliers, item_code):
    candidates = [s for s in suppliers if item_code in s.get("components", [])]
    if not candidates:
        return None
    max_lead = max(s["leadTime_days"] for s in candidates) or 1
    max_price = max(s["unitPrice_eur"] for s in candidates) or 1
    scored = []
    for s in candidates:
        score = (
            0.40 * s["reliability"]
            + 0.35 * (1 - s["leadTime_days"] / max_lead)
            + 0.25 * (1 - s["unitPrice_eur"] / max_price)
        )
        scored.append((score, s))
    scored.sort(key=lambda x: -x[0])
    return scored[0][1]


def compute_days_until_due(due_date_str):
    due = datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))
    return (due - datetime.now(timezone.utc)).days


def mvp_decide(missing_components, risk_steps, days_until_due, suppliers):
    if not missing_components:
        return "LANCER_IMMEDIAT"
    all_critical = any(mc["isCritical"] for mc in missing_components)
    longest_lead = 0
    for mc in missing_components:
        sup = find_best_supplier(suppliers, mc["itemCode"])
        if sup:
            longest_lead = max(longest_lead, sup["leadTime_days"])
        else:
            longest_lead = max(longest_lead, 999)
    earliest_cutoff_days = min((rs["time_to_reach_days"] for rs in risk_steps), default=0)
    if all_critical and longest_lead > days_until_due:
        return "REPORTER_ET_REPLANIFIER"
    if longest_lead <= earliest_cutoff_days + 1:
        return "LANCER_DECALE"
    if len(missing_components) >= 3 or longest_lead > days_until_due * 0.7:
        return "REPORTER_ET_REPLANIFIER"
    return "LANCER_DECALE"


# =============================================================================
# Supplier plan builder
# =============================================================================

def build_supplier_plan(missing_components, suppliers, of_number, today):
    plan, emails = [], []
    for mc in missing_components:
        sup = find_best_supplier(suppliers, mc["itemCode"])
        if not sup:
            continue
        order_date = today.strftime("%Y-%m-%d")
        eta = (today + timedelta(days=sup["leadTime_days"])).strftime("%Y-%m-%d")
        eta_display = (today + timedelta(days=sup["leadTime_days"])).strftime("%d/%m/%Y")
        plan.append({
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
        emails.append({
            "to": sup.get("contactEmail", sup.get("email", "")),
            "to_name": sup["name"],
            "supplier_id": sup["supplierId"],
            "subject": f"[URGENT] Order {mc['itemCode']} x {mc['qtyShortage']} -- {of_number}",
            "body": (
                f"Hello,\n\n"
                f"As part of {of_number}, we have an urgent need "
                f"for {mc['qtyShortage']} unit(s) of {mc['itemCode']}.\n\n"
                f"Current stock: {mc['qtyAvailable']} / Requirement: {mc['qtyNeeded']}\n"
                f"Requested delivery date: {eta_display}\n"
                f"Impact if delayed: blockage at production step\n\n"
                f"Please confirm availability and delivery lead time.\n\n"
                f"Best regards,\n"
                f"Maestro System -- Alstom AI Planning"
            ),
        })
    return plan, emails


def build_rescheduling_options(supplier_plan, machine_calendar, estimated_prod_days, due_date_str):
    if not supplier_plan:
        return []
    etas = [datetime.strptime(p["predicted_eta"], "%Y-%m-%d") for p in supplier_plan]
    latest_eta = max(etas)
    due = datetime.fromisoformat(due_date_str.replace("Z", "+00:00")).replace(tzinfo=None)
    launch_a = latest_eta
    completion_a = launch_a + timedelta(days=estimated_prod_days)
    delay_a = max(0, (completion_a - due).days)
    options = [{
        "label": f"Slot A -- Launch on {launch_a.strftime('%d/%m')} morning",
        "slot": f"SLOT-{launch_a.strftime('%Y-%m-%d')}-AM",
        "launch_date": launch_a.strftime("%Y-%m-%d"),
        "estimated_completion": completion_a.strftime("%Y-%m-%d"),
        "delay_client_days": delay_a,
        "penalty_eur": delay_a * 5000,
        "comment": f"All parts available. {delay_a}-day delay.",
    }]
    if len(etas) > 1:
        second_latest = sorted(etas)[-2]
        if second_latest < latest_eta:
            launch_b = second_latest
            completion_b = launch_b + timedelta(days=estimated_prod_days)
            delay_b = max(0, (completion_b - due).days)
            options.append({
                "label": f"Slot B -- Launch on {launch_b.strftime('%d/%m')} (partial risk)",
                "slot": f"SLOT-{launch_b.strftime('%Y-%m-%d')}-AM",
                "launch_date": launch_b.strftime("%Y-%m-%d"),
                "estimated_completion": completion_b.strftime("%Y-%m-%d"),
                "delay_client_days": delay_b,
                "penalty_eur": delay_b * 5000,
                "comment": "Some parts available, remaining expected shortly. Risk of blockage.",
            })
    return options


# =============================================================================
# AI layer -- Maestro agent
# =============================================================================

class MaestroAgent:
    def __init__(self, project_endpoint, deployment_name):
        self.project_endpoint = project_endpoint
        self.deployment_name = deployment_name

    async def analyze(self, context):
        from agent_framework.azure import AzureAIClient
        from azure.identity.aio import AzureCliCredential

        instructions = (
            "You are Maestro, an expert rail-industry production planner at Alstom.\n\n"
            "Given the full context of a Work Order (OF), produce a JSON object with:\n"
            "- risk_level: VERT | ORANGE | ROUGE\n"
            "- global_risk_score: 0-100\n"
            "- recommended_action: LANCER_IMMEDIAT | LANCER_DECALE | REPORTER_ET_REPLANIFIER\n"
            "- probabilite_blocage_pct: 0-100\n"
            "- estimated_delay_days: integer\n"
            "- estimated_penalty_eur: integer\n"
            "- maestro_message: executive summary for the operator\n"
            "- reasoning: detailed multi-line explanation\n"
            "- risk_factors: [{factor, score, detail}]\n"
            "- sla_impact: text about SLA consequences\n"
            "- recommended_launch_date: YYYY-MM-DD or null\n"
            "- recommended_launch_slot: SLOT-YYYY-MM-DD-AM/PM or null\n"
            "- estimated_production_days: integer\n"
            "- etape_a_risque: {operationId, sequence, description, time_to_reach_days, composant_manquant} or null\n\n"
            "Decision rules:\n"
            "- LANCER_IMMEDIAT: all components available, risk low\n"
            "- LANCER_DECALE: some parts missing but supplier ETA <= time-to-reach the blocking step\n"
            "- REPORTER_ET_REPLANIFIER: critical parts missing with long lead, delay certain\n\n"
            "Reply with a single valid JSON object. No markdown fences."
        )

        async with AzureCliCredential() as credential:
            async with AzureAIClient(credential=credential).create_agent(
                name="MaestroAgent",
                description="Maestro -- intelligent work-order planner",
                instructions=instructions,
            ) as agent:
                print(f"   [ok] AI agent created: {agent.id}")
                result = await agent.run(context)
                return json.loads(self._extract_json(result.text))

    @staticmethod
    def _extract_json(response):
        if "```json" in response:
            s = response.index("```json") + 7
            e = response.index("```", s)
            return response[s:e].strip()
        s = response.find("{")
        if s >= 0:
            e = response.rfind("}")
            return response[s:e + 1]
        raise ValueError("Could not extract JSON from AI response")


# =============================================================================
# LLM context builder
# =============================================================================

def build_llm_context(of, components, operations, stock, missing_components,
                      risk_steps, mvp_action, cutoff_op, last_doable_op,
                      supplier_plan, days_until_due,
                      historical_ofs, machine_calendar, sla_rules):
    lines = [
        "# Work-Order analysis context", "",
        "## Work Order",
        f"- ID: {of['id']}",
        f"- Product: {of['productCode']}",
        f"- Quantity: {of['quantity']}",
        f"- Priority: {of.get('priority', 'N/A')}",
        f"- Due date: {of.get('dueDate', 'N/A')}",
        f"- Days until due: {days_until_due}",
        "", "## BOM -- Components",
    ]
    for comp in components:
        qty_needed = comp["qtyPerUnit"] * of["quantity"]
        qty_avail = stock.get(comp["itemCode"], 0)
        crit = "CRITICAL" if comp.get("isCritical") else "standard"
        icon = "OK" if qty_avail >= qty_needed else "MISSING"
        lines.append(f"- [{icon}] {comp['itemCode']} ({crit}) -- need {qty_needed}, available {qty_avail}")
    lines += ["", "## Routing"]
    missing_codes = {mc["itemCode"] for mc in missing_components}
    for op in operations:
        req = set(op.get("requiredComponents", []))
        blocked = req & missing_codes
        icon = "BLOCKED" if blocked else "OK"
        cum_h = op.get("cumulative_start_hours", "?")
        lines.append(f"- seq.{op['sequence']} {op['operationId']} -- starts at {cum_h}h -- {icon}")
    if risk_steps:
        lines += ["", "## Risk steps"]
        for rs in risk_steps:
            lines.append(f"- {rs['itemCode']} blocks {rs['operationId']} reached in {rs['time_to_reach_days']}d, shortage {rs['qtyShortage']}")
    lines += ["", f"## MVP action: {mvp_action}"]
    if cutoff_op:
        lines.append(f"- Cutoff: {cutoff_op['operationId']} (seq.{cutoff_op['sequence']})")
    if supplier_plan:
        lines += ["", "## Supplier plan"]
        for sp in supplier_plan:
            lines.append(f"- {sp['itemCode']} -> {sp['supplier_name']}: {sp['order_qty']} pcs, lead {sp['estimated_lead_days']}d, ETA {sp['predicted_eta']}")
    if historical_ofs and historical_ofs.get("records"):
        lines += ["", "## History"]
        for rec in historical_ofs["records"][-5:]:
            late = f"{rec['daysLate']}d late" if rec["daysLate"] > 0 else "on-time"
            lines.append(f"- {rec['of_id']} -- qty {rec['quantity']}, {late}")
    if machine_calendar and machine_calendar.get("slots"):
        lines += ["", "## Machine slots"]
        for slot in machine_calendar["slots"]:
            if slot["status"] == "available":
                lines.append(f"- {slot['slotId']} -- {slot['date']} {slot['shift']} -- load {slot['currentLoad']*100:.0f}%")
    if sla_rules and sla_rules.get("rules"):
        lines += ["", "## SLA"]
        for rule in sla_rules["rules"]:
            lines.append(f"- {rule['client']} ({rule['serviceLevelAgreement']}): max {rule['maxAcceptableDelay_days']}d, penalty {rule['penaltyPerDayLate_eur']} eur/day")
    return "\n".join(lines)


# =============================================================================
# Output builder
# =============================================================================

def build_output(of, missing_components, risk_steps, cutoff_op, last_doable_op,
                 supplier_plan, simulated_emails, rescheduling_options,
                 days_until_due, ai=None, mvp_action="LANCER_IMMEDIAT"):
    """Builds the JSON output consumed by the Orchestrator and the Streamlit dashboards.

    Schema matches _SIMULATED_MAESTRO / run_maestro() from data.py."""
    now = datetime.now(timezone.utc)
    action = (ai or {}).get("recommended_action", mvp_action)
    risk_level_map = {"LANCER_IMMEDIAT": "VERT", "LANCER_DECALE": "ORANGE", "REPORTER_ET_REPLANIFIER": "ROUGE"}
    risk_level = (ai or {}).get("risk_level", risk_level_map.get(action, "ORANGE"))
    score = (ai or {}).get("global_risk_score",
              0 if action == "LANCER_IMMEDIAT" else 55 if action == "LANCER_DECALE" else 92)
    prob = (ai or {}).get("probabilite_blocage_pct",
             0 if not missing_components else 30 if action == "LANCER_DECALE" else 95)
    est_delay = (ai or {}).get("estimated_delay_days",
                 0 if action != "REPORTER_ET_REPLANIFIER" else 10)
    penalty = (ai or {}).get("estimated_penalty_eur", est_delay * 5000)
    prod_days = (ai or {}).get("estimated_production_days", 5)

    if ai and ai.get("etape_a_risque"):
        etape = ai["etape_a_risque"]
    elif risk_steps:
        rs = risk_steps[0]
        etape = {
            "operationId": rs["operationId"], "sequence": rs["sequence"],
            "description": rs["description"], "time_to_reach_days": rs["time_to_reach_days"],
            "composant_manquant": rs["itemCode"],
        }
    else:
        etape = None

    launch_date = (ai or {}).get("recommended_launch_date")
    launch_slot = (ai or {}).get("recommended_launch_slot")
    maestro_msg = (ai or {}).get("maestro_message", _default_message(action, missing_components))
    reasoning = (ai or {}).get("reasoning", "")
    risk_factors = (ai or {}).get("risk_factors", [])
    sla_impact = (ai or {}).get("sla_impact", "")

    return {
        "of_id": of["id"],
        "orderNumber": of["orderNumber"],
        "productCode": of["productCode"],
        "quantity": of["quantity"],
        "timestamp": now.isoformat(),
        "risk_level": risk_level,
        "global_risk_score": score,
        "probabilite_blocage_pct": prob,
        "etape_a_risque": etape,
        "risk_steps": risk_steps,
        "recommended_action": action,
        "recommended_launch_date": launch_date,
        "recommended_launch_slot": launch_slot,
        "estimated_production_days": prod_days,
        "days_until_due": days_until_due,
        "estimated_delay_days": est_delay,
        "estimated_penalty_eur": penalty,
        "maestro_message": maestro_msg,
        "reasoning": reasoning,
        "risk_factors": risk_factors,
        "sla_impact": sla_impact,
        "supplier_order_plan": supplier_plan,
        "simulated_emails": simulated_emails,
        "rescheduling_options": rescheduling_options,
        "missing_components": missing_components,
        "cutoff_operation": {
            "operationId": cutoff_op["operationId"],
            "sequence": cutoff_op["sequence"],
            "description": cutoff_op["description"],
        } if cutoff_op else None,
        "ai_enhanced": ai is not None,
        "operator_decision": None,
        "previous_status": of.get("status", "Created"),
        "new_status": "AwaitingDecision",
    }


def _default_message(action, missing):
    if action == "LANCER_IMMEDIAT":
        return "All components available. No blocking risk. Proceed as planned."
    parts = ", ".join(mc["itemCode"] for mc in missing)
    if action == "LANCER_DECALE":
        return f"Missing parts ({parts}) but supplier ETA within reach. Delayed launch recommended."
    return f"Critical shortage ({parts}). Rescheduling strongly recommended."


# =============================================================================
# Persistence & display
# =============================================================================

def persist_output(output, output_path):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"   Output written to: {output_path}")


def update_of_status(data_dir, of, new_status):
    of_path = os.path.join(data_dir, "of.json")
    of["status"] = new_status
    with open(of_path, "w", encoding="utf-8") as f:
        json.dump(of, f, indent=2, ensure_ascii=False)
    print(f"   OF updated: status -> {new_status}")


def print_summary(output):
    action = output["recommended_action"]
    print()
    print("=" * 70)
    print(f"  MAESTRO -- WORK-ORDER ANALYSIS: {output['of_id']}")
    print("=" * 70)
    print(f"  Risk level  : {output['risk_level']} ({output['global_risk_score']}/100)")
    print(f"  Action      : {action}")
    if output.get("recommended_launch_date"):
        print(f"  Launch slot : {output['recommended_launch_slot']} ({output['recommended_launch_date']})")
    if output.get("estimated_delay_days"):
        print(f"  Est. delay  : {output['estimated_delay_days']}d -- penalty {output['estimated_penalty_eur']} EUR")
    if output.get("missing_components"):
        print("  Missing parts:")
        for mc in output["missing_components"]:
            crit = " CRITICAL" if mc.get("isCritical") else ""
            print(f"    - {mc['itemCode']}{crit} -- need {mc['qtyNeeded']}, have {mc['qtyAvailable']}")
    if output.get("supplier_order_plan"):
        print("  Supplier orders:")
        for sp in output["supplier_order_plan"]:
            print(f"    -> {sp['itemCode']} -> {sp['supplier_name']}, {sp['order_qty']} pcs, ETA {sp['predicted_eta']}")
    if output.get("maestro_message"):
        print(f"\n  Message: {output['maestro_message']}")
    print(f"  Mode: {'AI-enhanced' if output.get('ai_enhanced') else 'Deterministic'}")
    print("=" * 70)
    print()


# =============================================================================
# Main
# =============================================================================

async def async_main(data_dir, output_path):
    print()
    print(">>> Maestro -- Intelligent work-order planner")
    print("-" * 50)

    print("[1/8] Loading work order...")
    of = load_of(data_dir)
    print("[2/8] Loading BOM and routing...")
    components, operations = load_bom_and_routing(data_dir, of["productCode"])
    print("[3/8] Loading stock...")
    stock = load_stock(data_dir)

    print("[4/8] Checking component availability...")
    missing_components = check_availability(components, of["quantity"], stock)
    risk_steps = find_risk_steps(operations, missing_components)
    cutoff_op = find_cutoff_operation(operations, missing_components)
    last_doable_op = find_last_doable_operation(operations, cutoff_op)
    for comp in components:
        qty_needed = comp["qtyPerUnit"] * of["quantity"]
        qty_avail = stock.get(comp["itemCode"], 0)
        icon = "[ok]" if qty_avail >= qty_needed else "[MISSING]"
        print(f"   {icon} {comp['itemCode']}: need {qty_needed}, available {qty_avail}")

    print("[5/8] Loading enrichment data...")
    suppliers_data = load_optional_json(data_dir, "suppliers.json")
    suppliers_list = suppliers_data.get("suppliers", []) if suppliers_data else []
    historical_ofs = load_optional_json(data_dir, "historical_ofs.json")
    machine_calendar = load_optional_json(data_dir, "machine_calendar.json")
    sla_rules = load_optional_json(data_dir, "sla_rules.json")
    days_until_due = compute_days_until_due(of.get("dueDate", "2099-12-31T00:00:00Z"))

    print("[6/8] Deterministic decision...")
    mvp_action = mvp_decide(missing_components, risk_steps, days_until_due, suppliers_list)
    print(f"   MVP action: {mvp_action}")

    today = datetime.now(timezone.utc)
    supplier_plan, simulated_emails = build_supplier_plan(
        missing_components, suppliers_list, of["orderNumber"], today)
    rescheduling_options = []
    if mvp_action == "REPORTER_ET_REPLANIFIER":
        rescheduling_options = build_rescheduling_options(
            supplier_plan, machine_calendar, 5, of.get("dueDate", "2099-12-31T00:00:00Z"))

    ai_result = None
    project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT") or os.getenv("AI_FOUNDRY_PROJECT_ENDPOINT")
    deployment_name = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4.1")

    if project_endpoint:
        print("[7/8] Calling AI agent...")
        try:
            context = build_llm_context(
                of, components, operations, stock, missing_components,
                risk_steps, mvp_action, cutoff_op, last_doable_op,
                supplier_plan, days_until_due,
                historical_ofs, machine_calendar, sla_rules)
            agent = MaestroAgent(project_endpoint, deployment_name)
            ai_result = await agent.analyze(context)
            print(f"   AI -> action: {ai_result.get('recommended_action')}")
            print(f"   AI -> risk: {ai_result.get('global_risk_score')}/100 ({ai_result.get('risk_level')})")
        except Exception as e:
            logger.exception("AI analysis failed")
            print(f"   [warn] AI error: {e} -- falling back to deterministic mode")
    else:
        print("[7/8] Azure AI not configured -- deterministic mode only")

    output_file = output_path or os.path.join(data_dir, f"agent1_output_{of['id']}.json")
    print("[8/8] Building output & persisting...")
    output = build_output(
        of=of, missing_components=missing_components, risk_steps=risk_steps,
        cutoff_op=cutoff_op, last_doable_op=last_doable_op,
        supplier_plan=supplier_plan, simulated_emails=simulated_emails,
        rescheduling_options=rescheduling_options, days_until_due=days_until_due,
        ai=ai_result, mvp_action=mvp_action)
    persist_output(output, output_file)
    update_of_status(data_dir, of, output["new_status"])
    print_summary(output)


def main():
    parser = argparse.ArgumentParser(description="Maestro -- Intelligent work-order planner")
    parser.add_argument("--data-dir", default=os.path.join(os.path.dirname(__file__), "..", "data"))
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    asyncio.run(async_main(os.path.abspath(args.data_dir), args.output))


if __name__ == "__main__":
    main()
