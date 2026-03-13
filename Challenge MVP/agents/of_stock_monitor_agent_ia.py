#!/usr/bin/env python3
"""Sentinel -- Parts-arrival monitoring and risk-update agent.

For each Work Order on the watchlist (fed by the Orchestrator from Maestro outputs):
  * Tracks missing-material arrivals (compares current stock with Maestro shortage list)
  * Reassesses blocking risk as production progresses

Case 1 -- risk cleared (parts arrived)
  * Clears the warning, updates risk to VERT
  * Produces a JSON READY output with instructions to resume production

Case 2 -- risk active (parts still missing)
  * Uses the LLM to recompute ETA and delay impact
  * Keeps the WO on the watchlist
  * Produces a JSON NOT_READY output with updated risk, supplier recommendations,
    rescheduling proposal, and supervisor notification

Fallback: if Azure AI is not configured the agent runs in pure deterministic mode.

Usage:
    python agents/of_stock_monitor_agent_ia.py [--data-dir DATA_DIR]
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

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


def load_orders_to_watch(data_dir: str) -> List[Dict]:
    data = load_json(os.path.join(data_dir, "orders_partially_released.json"))
    orders = [o for o in data["orders"] if o["status"] in ("PartiallyReleased", "Delayed", "UnderMonitoring")]
    print(f"   {len(orders)} WO(s) to monitor")
    return orders


def load_agent1_output(data_dir: str, of_id: str, agent1_output_file: Optional[str] = None) -> Dict:
    candidates = []
    if agent1_output_file:
        candidates.append(os.path.join(data_dir, agent1_output_file))
    candidates.append(os.path.join(data_dir, f"agent1_output_{of_id}.json"))
    candidates.append(os.path.join(data_dir, "agent1_output.json"))
    for path in candidates:
        if os.path.exists(path):
            state = load_json(path)
            print(f"   Maestro output loaded: {os.path.basename(path)}")
            if state.get("of_id") != of_id:
                raise ValueError(f"Maestro output of_id={state.get('of_id')}, expected {of_id}")
            return state
    raise FileNotFoundError(f"No Maestro output for {of_id}")


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
# Deterministic logic
# =============================================================================

def check_shortages_resolved(missing_components, stock):
    resolved, still_missing = [], []
    for mc in missing_components:
        available = stock.get(mc["itemCode"], 0)
        if available >= mc["qtyNeeded"]:
            resolved.append({
                "itemCode": mc["itemCode"],
                "description": mc.get("description", ""),
                "qtyNeeded": mc["qtyNeeded"],
                "qtyAvailableNow": available,
            })
        else:
            still_missing.append({
                "itemCode": mc["itemCode"],
                "description": mc.get("description", ""),
                "qtyNeeded": mc["qtyNeeded"],
                "qtyAvailableNow": available,
                "qtyStillShort": mc["qtyNeeded"] - available,
                "isCritical": mc.get("isCritical", False),
            })
    return resolved, still_missing


def build_parts_tracking(maestro_output, resolved_codes, stock):
    """Build the parts_tracking array from Maestro supplier plan."""
    tracking = []
    for plan in maestro_output.get("supplier_order_plan", []):
        item = plan["itemCode"]
        if item in resolved_codes:
            tracking.append({
                "itemCode": item,
                "initial_status": "MANQUANT",
                "current_status": "RECU",
                "supplier": plan["supplier_name"],
                "eta_initial": plan["predicted_eta"],
                "eta_updated": plan["predicted_eta"],
                "qty_received": stock.get(item, 0),
            })
        else:
            tracking.append({
                "itemCode": item,
                "initial_status": "MANQUANT",
                "current_status": "EN_ATTENTE",
                "supplier": plan["supplier_name"],
                "eta_initial": plan["predicted_eta"],
                "eta_updated": plan["predicted_eta"],
                "qty_received": 0,
            })
    return tracking


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


def build_supplier_recommendations(still_missing, suppliers):
    """For each still-missing part, build a supplier recommendation."""
    recs = []
    today = datetime.now(timezone.utc)
    for sm in still_missing:
        sup = find_best_supplier(suppliers, sm["itemCode"])
        if not sup:
            continue
        eta = (today + timedelta(days=sup["leadTime_days"])).strftime("%Y-%m-%d")
        recs.append({
            "itemCode": sm["itemCode"],
            "recommended_supplier": sup["supplierId"],
            "supplier_name": sup["name"],
            "supplier_score": int(sup["reliability"] * 100),
            "order_qty": sm["qtyStillShort"],
            "unit_price_eur": sup["unitPrice_eur"],
            "total_price_eur": sup["unitPrice_eur"] * sm["qtyStillShort"],
            "estimated_lead_days": sup["leadTime_days"],
            "predicted_eta": eta,
            "confidence": sup["reliability"],
        })
    return recs


# =============================================================================
# AI layer -- Sentinel agent
# =============================================================================

class SentinelAgent:
    def __init__(self, project_endpoint, deployment_name):
        self.project_endpoint = project_endpoint
        self.deployment_name = deployment_name

    async def analyze(self, context):
        from agent_framework.azure import AzureAIClient
        from azure.identity.aio import AzureCliCredential

        instructions = (
            "You are Sentinel, an expert parts-arrival monitor for Alstom rail production.\n\n"
            "Given the context of a Work Order still on the watchlist, produce a JSON with:\n"
            "- current_risk_level: VERT | ORANGE | ROUGE\n"
            "- risk_evolution: BAISSE | STABLE | HAUSSE\n"
            "- warning_status: LEVE | EN_SURVEILLANCE | CONFIRME\n"
            "- sentinelle_message: concise status message for the supervisor\n"
            "- updated_delay_days: integer (0 if risk cleared)\n"
            "- resume_priority: 1-5 (1=urgent resume, 5=can wait)\n"
            "- resume_priority_reasoning: explanation\n"
            "- plan_b_needed: boolean\n"
            "- rescheduling_proposal: {label, slot, launch_date, estimated_completion, delay_client_days, penalty_eur} or null\n"
            "- parts_tracking: [{itemCode, initial_status, current_status, supplier, eta_initial, eta_updated, qty_received}]\n\n"
            "Risk cleared = all parts arrived => VERT, warning LEVE, delay 0, priority 1.\n"
            "Risk active = parts still missing => keep ORANGE/ROUGE, propose rescheduling if plan_b_needed.\n\n"
            "Reply with a single valid JSON object. No markdown fences."
        )

        async with AzureCliCredential() as credential:
            async with AzureAIClient(credential=credential).create_agent(
                name="SentinelAgent",
                description="Sentinel -- parts-arrival monitor",
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


def build_sentinel_context(of_id, of_priority, of_due_date, maestro_output,
                            resolved, still_missing, parts_tracking,
                            suppliers_data, sla_rules):
    lines = [
        "# Sentinel -- Parts arrival check", "",
        "## Work Order",
        f"- ID: {of_id}",
        f"- Priority: {of_priority}",
        f"- Due date: {of_due_date}",
        f"- Maestro action: {maestro_output.get('recommended_action', 'N/A')}",
        f"- Maestro risk: {maestro_output.get('risk_level', '?')} ({maestro_output.get('global_risk_score', '?')}/100)",
    ]
    if resolved:
        lines += ["", "## Parts received"]
        for r in resolved:
            lines.append(f"- {r['itemCode']} -- available {r['qtyAvailableNow']} >= need {r['qtyNeeded']}")
    if still_missing:
        lines += ["", "## Parts still missing"]
        for sm in still_missing:
            crit = " CRITICAL" if sm.get("isCritical") else ""
            lines.append(f"- {sm['itemCode']}{crit} -- need {sm['qtyNeeded']}, have {sm['qtyAvailableNow']}, short {sm['qtyStillShort']}")
    if parts_tracking:
        lines += ["", "## Parts tracking"]
        for pt in parts_tracking:
            lines.append(f"- {pt['itemCode']}: {pt['current_status']} (supplier: {pt['supplier']}, ETA: {pt['eta_updated']})")
    if maestro_output.get("rescheduling_options"):
        lines += ["", "## Available rescheduling options"]
        for opt in maestro_output["rescheduling_options"]:
            lines.append(f"- {opt['label']}: launch {opt['launch_date']}, delay {opt['delay_client_days']}d, penalty {opt['penalty_eur']} EUR")
    if sla_rules and sla_rules.get("rules"):
        lines += ["", "## SLA"]
        for rule in sla_rules["rules"]:
            lines.append(f"- {rule['client']}: max delay {rule['maxAcceptableDelay_days']}d, penalty {rule['penaltyPerDayLate_eur']} EUR/day")
    return "\n".join(lines)


# =============================================================================
# Output builder
# =============================================================================

def build_output(of_id, previous_status, maestro_output,
                 resolved, still_missing, parts_tracking,
                 supplier_recommendations, ai=None):
    """Builds sentinel output matching _SIMULATED_SENTINELLE from data.py."""
    now = datetime.now(timezone.utc).isoformat()
    initial_risk = maestro_output.get("risk_level", "?")

    # Case 1: risk cleared
    if not still_missing:
        current_risk = (ai or {}).get("current_risk_level", "VERT")
        risk_evo = (ai or {}).get("risk_evolution", "BAISSE")
        warning = (ai or {}).get("warning_status", "LEVE")
        message = (ai or {}).get("sentinelle_message",
            "Parts received. Blockage risk cleared. Production can continue normally.")
        delay = 0
        priority = 1
        priority_reason = (ai or {}).get("resume_priority_reasoning",
            "Parts available, no residual risk. Immediate resumption recommended.")
        plan_b = False
        resched = None
    # Case 2: risk still active
    else:
        current_risk = (ai or {}).get("current_risk_level", initial_risk)
        risk_evo = (ai or {}).get("risk_evolution", "STABLE")
        warning = (ai or {}).get("warning_status", "CONFIRME")
        parts_str = ", ".join(sm["itemCode"] for sm in still_missing)
        message = (ai or {}).get("sentinelle_message",
            f"Parts still missing: {parts_str}. Risk remains active.")
        delay = (ai or {}).get("updated_delay_days", maestro_output.get("estimated_delay_days", 0))
        priority = (ai or {}).get("resume_priority", 5)
        priority_reason = (ai or {}).get("resume_priority_reasoning",
            f"Missing parts: {parts_str}. Awaiting receipt.")
        plan_b = (ai or {}).get("plan_b_needed", True)
        resched_options = maestro_output.get("rescheduling_options", [])
        resched = (ai or {}).get("rescheduling_proposal", resched_options[0] if resched_options else None)

    return {
        "of_id": of_id,
        "previous_status": previous_status,
        "new_status": "ReadyToResume" if not still_missing else "PartiallyReleased",
        "timestamp": now,
        "initial_risk_level": initial_risk,
        "current_risk_level": current_risk,
        "risk_evolution": risk_evo,
        "warning_status": warning,
        "sentinelle_message": message,
        "parts_tracking": (ai or {}).get("parts_tracking", parts_tracking),
        "resolved_components": resolved,
        "still_missing_components": still_missing,
        "updated_eta_end": None,
        "updated_delay_days": delay,
        "resume_priority": priority,
        "resume_priority_reasoning": priority_reason,
        "plan_b_needed": plan_b,
        "rescheduling_proposal": resched,
        "supplier_recommendations": supplier_recommendations,
        "ai_enhanced": ai is not None,
    }


# =============================================================================
# Persistence & display
# =============================================================================

def persist_output(output, output_path):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"   Output written to: {output_path}")


def update_of_status(data_dir, of_id, new_status):
    of_path = os.path.join(data_dir, "of.json")
    if not os.path.exists(of_path):
        return
    of = load_json(of_path)
    if of.get("id") == of_id:
        of["status"] = new_status
        with open(of_path, "w", encoding="utf-8") as f:
            json.dump(of, f, indent=2, ensure_ascii=False)
        print(f"   OF updated: status -> {new_status}")


def notify(output):
    of_id = output["of_id"]
    status = output["new_status"]
    if status == "ReadyToResume":
        parts = ", ".join(r["itemCode"] for r in output["resolved_components"])
        print(f"   >>> NOTIFICATION: OF {of_id} ready to resume. Parts available: {parts}.")
    else:
        shortage = ", ".join(f"{sm['itemCode']} (short {sm['qtyStillShort']})" for sm in output["still_missing_components"])
        print(f"   >>> NOTIFICATION: OF {of_id} still waiting. Missing: {shortage}.")
    if output.get("sentinelle_message"):
        print(f"   Message: {output['sentinelle_message']}")


def print_summary(results):
    ready = [r for r in results if r["new_status"] == "ReadyToResume"]
    waiting = [r for r in results if r["new_status"] != "ReadyToResume"]
    print()
    print("=" * 70)
    print("  SENTINEL -- PARTS MONITORING SUMMARY")
    print("=" * 70)
    print(f"  WOs processed      : {len(results)}")
    print(f"  Ready to resume    : {len(ready)}")
    print(f"  Still waiting      : {len(waiting)}")
    if ready:
        print("\n  Ready:")
        for r in ready:
            print(f"    - {r['of_id']} -> resume production")
    if waiting:
        print("\n  Waiting:")
        for r in waiting:
            parts = ", ".join(sm["itemCode"] for sm in r["still_missing_components"])
            prio = f" [priority {r.get('resume_priority', '?')}/5]" if r.get("resume_priority") else ""
            print(f"    - {r['of_id']}{prio} -> missing: {parts}")
            for rec in r.get("supplier_recommendations", []):
                print(f"      -> {rec['itemCode']} via {rec['supplier_name']}, ETA {rec['predicted_eta']}")
    print("=" * 70)
    print()


# =============================================================================
# Main
# =============================================================================

async def async_main(data_dir):
    print()
    print(">>> Sentinel -- Parts-arrival monitoring agent")
    print("-" * 55)

    print("[1/7] Loading watchlist...")
    orders = load_orders_to_watch(data_dir)
    if not orders:
        print("   No WOs to monitor. Done.")
        return

    print("[2/7] Loading current stock...")
    stock = load_stock(data_dir)

    print("[ ] Loading enrichment data...")
    suppliers_data = load_optional_json(data_dir, "suppliers.json")
    suppliers_list = suppliers_data.get("suppliers", []) if suppliers_data else []
    sla_rules = load_optional_json(data_dir, "sla_rules.json")

    project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT") or os.getenv("AI_FOUNDRY_PROJECT_ENDPOINT")
    deployment_name = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4.1")

    results = []

    for order in orders:
        of_id = order["of_id"]
        print(f"\n  --- Processing WO: {of_id}")

        print(f"  [3/7] Loading Maestro output...")
        try:
            maestro_output = load_agent1_output(
                data_dir, of_id, agent1_output_file=order.get("agent1_output_file"))
        except (FileNotFoundError, ValueError) as e:
            print(f"  [warn] {e}")
            print(f"  --- WO {of_id} skipped")
            continue

        missing_components = maestro_output.get("missing_components", [])

        print(f"  [4/7] Checking shortages...")
        resolved, still_missing = check_shortages_resolved(missing_components, stock)
        for r in resolved:
            print(f"    [ok] {r['itemCode']} -- available {r['qtyAvailableNow']} >= need {r['qtyNeeded']}")
        for sm in still_missing:
            crit = " CRITICAL" if sm.get("isCritical") else ""
            print(f"    [MISSING] {sm['itemCode']}{crit} -- available {sm['qtyAvailableNow']} < need {sm['qtyNeeded']}")

        resolved_codes = {r["itemCode"] for r in resolved}
        parts_tracking = build_parts_tracking(maestro_output, resolved_codes, stock)
        supplier_recs = build_supplier_recommendations(still_missing, suppliers_list)

        # AI analysis (only if parts still missing and AI is available)
        ai_result = None
        if still_missing and project_endpoint:
            print(f"  [5b] Calling AI agent...")
            try:
                of_priority = order.get("priority", "N/A")
                of_due_date = order.get("dueDate", "N/A")
                context = build_sentinel_context(
                    of_id, of_priority, of_due_date, maestro_output,
                    resolved, still_missing, parts_tracking,
                    suppliers_data, sla_rules)
                sentinel = SentinelAgent(project_endpoint, deployment_name)
                ai_result = await sentinel.analyze(context)
                print(f"    AI -> risk: {ai_result.get('current_risk_level')}, priority: {ai_result.get('resume_priority')}/5")
            except Exception as e:
                logger.exception("AI analysis failed")
                print(f"    [warn] AI error: {e} -- deterministic mode")
        elif still_missing:
            print(f"  [5b] Azure AI not configured -- deterministic mode")

        print(f"  [6/7] Building output...")
        output = build_output(
            of_id=of_id,
            previous_status=order["status"],
            maestro_output=maestro_output,
            resolved=resolved,
            still_missing=still_missing,
            parts_tracking=parts_tracking,
            supplier_recommendations=supplier_recs,
            ai=ai_result)

        print(f"  [7/7] Persisting & notifying...")
        output_path = os.path.join(data_dir, f"agent2_output_{of_id}.json")
        persist_output(output, output_path)
        if output["new_status"] == "ReadyToResume":
            update_of_status(data_dir, of_id, "ReadyToResume")
        notify(output)
        results.append(output)
        print(f"  --- WO {of_id} done")

    print_summary(results)


def main():
    parser = argparse.ArgumentParser(description="Sentinel -- Parts-arrival monitoring agent")
    parser.add_argument("--data-dir", default=os.path.join(os.path.dirname(__file__), "..", "data"))
    args = parser.parse_args()
    asyncio.run(async_main(os.path.abspath(args.data_dir)))


if __name__ == "__main__":
    main()
