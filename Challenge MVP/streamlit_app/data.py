"""Seed data et logique simulée des agents OF.

Contient :
  - Les 3 scénarios de démonstration (OK / Moyen / Critique)
  - Les fonctions run_agent1, run_orchestrator, run_agent2
  - Les outputs IA simulés (pas d'appel LLM)

Pour brancher la vraie logique plus tard, remplacer les fonctions
run_agent1 / run_agent2 par les appels aux scripts :
  - agents/of_planning_agent_ia.py
  - agents/of_stock_monitor_agent_ia.py
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import copy
import json
import os


# =============================================================================
# Seed data — 3 scénarios
# =============================================================================

def build_seed_orders() -> Dict[str, Dict]:
    """Retourne les 3 OF de démonstration indexés par of_id."""
    return {
        "of-2026-00200": {
            "of_id": "of-2026-00200",
            "scenario": "OK",
            "scenario_label": "✅ Scénario OK — Stock complet",
            "orderNumber": "OF-2026-00200",
            "productCode": "BOGIE_Y32",
            "quantity": 2,
            "priority": "Medium",
            "status": "Created",
            "dueDate": "2026-04-10T00:00:00Z",
            "components": [
                {"itemCode": "BOGIE_FRAME_Y32", "qtyPerUnit": 1, "isCritical": True},
                {"itemCode": "WHEELSET_920MM",  "qtyPerUnit": 2, "isCritical": True},
                {"itemCode": "AXLE_BOX",        "qtyPerUnit": 4, "isCritical": False},
                {"itemCode": "SUSPENSION_SPRING","qtyPerUnit": 4, "isCritical": False},
                {"itemCode": "BRAKE_DISC",      "qtyPerUnit": 4, "isCritical": True},
                {"itemCode": "TRACTION_MOTOR_TM","qtyPerUnit": 2, "isCritical": True},
            ],
            "stock": {
                "BOGIE_FRAME_Y32": 5,
                "WHEELSET_920MM": 10,
                "AXLE_BOX": 20,
                "SUSPENSION_SPRING": 18,
                "BRAKE_DISC": 20,
                "TRACTION_MOTOR_TM": 9,
            },
            "historical_risk": "LOW",
        },
        "of-2026-00201": {
            "of_id": "of-2026-00201",
            "scenario": "Moyen",
            "scenario_label": "⚠️ Scénario Moyen — 1 pièce manquante",
            "orderNumber": "OF-2026-00201",
            "productCode": "BOGIE_Y32",
            "quantity": 4,
            "priority": "High",
            "status": "Created",
            "dueDate": "2026-03-25T00:00:00Z",
            "components": [
                {"itemCode": "BOGIE_FRAME_Y32", "qtyPerUnit": 1, "isCritical": True},
                {"itemCode": "WHEELSET_920MM",  "qtyPerUnit": 2, "isCritical": True},
                {"itemCode": "AXLE_BOX",        "qtyPerUnit": 4, "isCritical": False},
                {"itemCode": "SUSPENSION_SPRING","qtyPerUnit": 4, "isCritical": False},
                {"itemCode": "BRAKE_DISC",      "qtyPerUnit": 4, "isCritical": True},
                {"itemCode": "TRACTION_MOTOR_TM","qtyPerUnit": 2, "isCritical": True},
            ],
            "stock": {
                "BOGIE_FRAME_Y32": 6,
                "WHEELSET_920MM": 10,
                "AXLE_BOX": 20,
                "SUSPENSION_SPRING": 18,
                "BRAKE_DISC": 0,       # ← manquant
                "TRACTION_MOTOR_TM": 9,
            },
            "historical_risk": "MEDIUM",
        },
        "of-2026-00202": {
            "of_id": "of-2026-00202",
            "scenario": "Critique",
            "scenario_label": "🛑 Scénario Critique — Plusieurs pièces critiques manquantes",
            "orderNumber": "OF-2026-00202",
            "productCode": "BOGIE_Y32",
            "quantity": 6,
            "priority": "High",
            "status": "Created",
            "dueDate": "2026-03-20T00:00:00Z",
            "components": [
                {"itemCode": "BOGIE_FRAME_Y32", "qtyPerUnit": 1, "isCritical": True},
                {"itemCode": "WHEELSET_920MM",  "qtyPerUnit": 2, "isCritical": True},
                {"itemCode": "AXLE_BOX",        "qtyPerUnit": 4, "isCritical": False},
                {"itemCode": "SUSPENSION_SPRING","qtyPerUnit": 4, "isCritical": False},
                {"itemCode": "BRAKE_DISC",      "qtyPerUnit": 4, "isCritical": True},
                {"itemCode": "TRACTION_MOTOR_TM","qtyPerUnit": 2, "isCritical": True},
            ],
            "stock": {
                "BOGIE_FRAME_Y32": 6,
                "WHEELSET_920MM": 4,   # ← manquant (besoin 12)
                "AXLE_BOX": 20,
                "SUSPENSION_SPRING": 18,
                "BRAKE_DISC": 0,       # ← manquant (besoin 24)
                "TRACTION_MOTOR_TM": 2, # ← manquant (besoin 12)
            },
            "historical_risk": "HIGH",
        },
    }


# Gamme commune
ROUTING = [
    {"operationId": "OP10_FRAME_PREP",      "sequence": 10, "description": "Préparation châssis",           "requiredComponents": ["BOGIE_FRAME_Y32"]},
    {"operationId": "OP20_WHEELSET_MOUNT",   "sequence": 20, "description": "Montage essieux + boîtes",     "requiredComponents": ["WHEELSET_920MM", "AXLE_BOX"]},
    {"operationId": "OP30_SUSPENSION",       "sequence": 30, "description": "Installation suspension",       "requiredComponents": ["SUSPENSION_SPRING"]},
    {"operationId": "OP40_BRAKE_ASSEMBLY",   "sequence": 40, "description": "Montage freins",                "requiredComponents": ["BRAKE_DISC"]},
    {"operationId": "OP50_TRACTION_MOTOR",   "sequence": 50, "description": "Installation moteur traction",  "requiredComponents": ["TRACTION_MOTOR_TM"]},
    {"operationId": "OP60_TESTING",          "sequence": 60, "description": "Tests et contrôle qualité",     "requiredComponents": []},
]


# =============================================================================
# Agent 1 — Planification OF (simulé)
# =============================================================================

def _check_availability(components, quantity, stock):
    """Calcule les composants manquants."""
    missing = []
    for comp in components:
        needed = comp["qtyPerUnit"] * quantity
        available = stock.get(comp["itemCode"], 0)
        if available < needed:
            missing.append({
                "itemCode": comp["itemCode"],
                "qtyNeeded": needed,
                "qtyAvailable": available,
                "qtyShortage": needed - available,
                "isCritical": comp.get("isCritical", False),
            })
    return missing


def _find_cutoff(operations, missing_components):
    """Trouve la 1ère opération bloquée par un composant manquant."""
    missing_codes = {mc["itemCode"] for mc in missing_components}
    for op in operations:
        if set(op.get("requiredComponents", [])) & missing_codes:
            return op
    return None


def _find_last_doable(operations, cutoff_op):
    """Dernière opération faisable avant la coupure."""
    if cutoff_op is None:
        return None
    cutoff_seq = cutoff_op["sequence"]
    doable = [op for op in operations if op["sequence"] < cutoff_seq]
    return doable[-1] if doable else None


# Outputs IA simulés par scénario
_SIMULATED_AI_AGENT1 = {
    "OK": {
        "decision": "FULL_RELEASE",
        "global_risk_score": 12,
        "risk_level": "LOW",
        "recommended_start_slot": "SLOT-2026-03-12-AM",
        "estimated_production_days": 3,
        "sla_impact": "Aucun risque SLA — livraison bien avant l'échéance.",
        "reasoning": (
            "Tous les composants sont disponibles en quantité suffisante. "
            "L'historique ne montre aucun blocage récent sur ce type d'OF. "
            "Le créneau du 12/03 matin est peu chargé (30%). "
            "Recommandation : lancer la production complète immédiatement."
        ),
        "risk_factors": [
            {"factor": "Stock", "score": 5, "detail": "Tous composants disponibles"},
            {"factor": "Historique", "score": 10, "detail": "Aucun retard récent"},
            {"factor": "Planning", "score": 15, "detail": "Créneaux dégagés"},
        ],
    },
    "Moyen": {
        "decision": "PARTIAL_RELEASE",
        "global_risk_score": 62,
        "risk_level": "MEDIUM",
        "recommended_start_slot": "SLOT-2026-03-11-AM",
        "estimated_production_days": 2,
        "sla_impact": (
            "Si le réappro BRAKE_DISC arrive sous 3 jours, l'OF reste dans le SLA. "
            "Au-delà, pénalité de 5 000 €/jour (contrat SNCF_TGV Premium)."
        ),
        "reasoning": (
            "Le composant BRAKE_DISC (critique) est totalement absent du stock. "
            "La production peut avancer jusqu'à OP30_SUSPENSION inclus, ce qui couvre "
            "~60% de la valeur ajoutée. L'historique montre 3 à 4 jours de retard sur "
            "des OF similaires bloqués par BRAKE_DISC. Le créneau SLOT-2026-03-11-AM "
            "est à 30% de charge, idéal pour un démarrage partiel."
        ),
        "risk_factors": [
            {"factor": "Composants critiques manquants", "score": 80, "detail": "BRAKE_DISC totalement absent"},
            {"factor": "Historique retards", "score": 60, "detail": "3-4j retard sur OF similaires"},
            {"factor": "SLA SNCF_TGV", "score": 70, "detail": "Max 2j retard, 5000€/j pénalité"},
            {"factor": "Planning machine", "score": 20, "detail": "Créneaux disponibles"},
        ],
    },
    "Critique": {
        "decision": "DELAYED_RELEASE",
        "global_risk_score": 88,
        "risk_level": "HIGH",
        "recommended_start_slot": None,
        "estimated_production_days": None,
        "sla_impact": (
            "SLA déjà compromis — échéance 20/03, réappro estimé à 10+ jours. "
            "Pénalités probables : 5 000 €/jour × 8+ jours = 40 000 €+."
        ),
        "reasoning": (
            "3 composants critiques manquants (WHEELSET_920MM, BRAKE_DISC, TRACTION_MOTOR_TM). "
            "Le lancement partiel n'apporterait que OP10 (préparation châssis), soit ~15% de valeur ajoutée. "
            "L'historique montre 7 jours d'attente stock sur des scénarios comparables. "
            "Recommandation : différer l'OF et prioriser un OF concurrent moins bloqué."
        ),
        "risk_factors": [
            {"factor": "Composants critiques manquants", "score": 95, "detail": "3 pièces critiques absentes"},
            {"factor": "Historique retards", "score": 85, "detail": "7j attente stock historique"},
            {"factor": "SLA", "score": 90, "detail": "Échéance 20/03 intenable"},
            {"factor": "Planning machine", "score": 30, "detail": "Mais inutile sans pièces"},
        ],
    },
}


def run_agent1(of_id: str, orders: Dict) -> Dict:
    """Simule l'Agent 1 sur un OF donné. Retourne l'output Agent 1."""
    order = orders[of_id]
    scenario = order["scenario"]
    components = order["components"]
    quantity = order["quantity"]
    stock = order["stock"]

    # --- Étapes déterministes (identiques au vrai agent) ---
    missing = _check_availability(components, quantity, stock)
    cutoff_op = _find_cutoff(ROUTING, missing)
    last_doable = _find_last_doable(ROUTING, cutoff_op)

    # --- Décision IA simulée ---
    ai = _SIMULATED_AI_AGENT1[scenario]
    decision = ai["decision"]

    # Construction de l'output (même schéma que le vrai agent)
    now = datetime.now(timezone.utc).isoformat()
    output = {
        "of_id": of_id,
        "orderNumber": order["orderNumber"],
        "productCode": order["productCode"],
        "quantity": quantity,
        "decision": decision,
        "previous_status": order["status"],
        "timestamp": now,
        "ai_enhanced": True,
        "global_risk_score": ai["global_risk_score"],
        "risk_level": ai["risk_level"],
        "risk_factors": ai["risk_factors"],
        "recommended_start_slot": ai["recommended_start_slot"],
        "estimated_production_days": ai["estimated_production_days"],
        "sla_impact": ai["sla_impact"],
        "ai_reasoning": ai["reasoning"],
    }

    if decision == "FULL_RELEASE":
        output["new_status"] = "Released"
        output["missing_components"] = []
        output["cutoff_operation"] = None
        output["resume_from_operation"] = None
        output["instruction"] = "Production normale — tous les composants sont disponibles."

    elif decision == "PARTIAL_RELEASE":
        output["new_status"] = "PartiallyReleased"
        output["missing_components"] = missing
        output["cutoff_operation"] = {
            "operationId": cutoff_op["operationId"],
            "sequence": cutoff_op["sequence"],
            "description": cutoff_op["description"],
        } if cutoff_op else None
        output["resume_from_operation"] = {
            "operationId": cutoff_op["operationId"],
            "sequence": cutoff_op["sequence"],
        } if cutoff_op else None
        shortage_parts = ", ".join(
            f"{mc['itemCode']} (manque {mc['qtyShortage']})" for mc in missing
        )
        last_op_label = last_doable["operationId"] if last_doable else "?"
        output["instruction"] = (
            f"Produire jusqu'à {last_op_label} inclus, "
            f"puis mettre de côté en attente de : {shortage_parts}"
        )

    elif decision == "DELAYED_RELEASE":
        output["new_status"] = "Delayed"
        output["missing_components"] = missing
        output["cutoff_operation"] = None
        output["resume_from_operation"] = None
        critical = [mc["itemCode"] for mc in missing if mc.get("isCritical")]
        output["instruction"] = (
            f"OF mis en attente — composants critiques manquants : {', '.join(critical)}. "
            f"Risque SLA trop élevé pour un lancement partiel."
        )

    # Mettre à jour le statut de l'OF en mémoire
    order["status"] = output["new_status"]
    order["last_agent"] = "Agent 1"

    return output


# =============================================================================
# Orchestrateur (simulé)
# =============================================================================

def run_orchestrator(agent1_outputs: Dict) -> List[Dict]:
    """Scanne les outputs Agent 1 et retourne la watchlist pour Agent 2."""
    watchlist = []
    for of_id, output in agent1_outputs.items():
        if output.get("new_status") in ("PartiallyReleased", "Delayed"):
            watchlist.append({
                "of_id": of_id,
                "status": output["new_status"],
                "productCode": output["productCode"],
                "decision": output["decision"],
                "risk_level": output.get("risk_level", "?"),
            })
    return watchlist


# =============================================================================
# Agent 2 — Surveillance stock & reprise (simulé)
# =============================================================================

# Stock simulé "après réappro" pour chaque scénario
_SIMULATED_STOCK_AGENT2 = {
    "Moyen": {
        # BRAKE_DISC est revenu en stock
        "BRAKE_DISC": 20,
    },
    "Critique": {
        # Rien n'est revenu
        "WHEELSET_920MM": 4,
        "BRAKE_DISC": 0,
        "TRACTION_MOTOR_TM": 2,
    },
}

_SIMULATED_AI_AGENT2 = {
    "Moyen": {
        "resume_priority": 1,
        "resume_priority_reasoning": (
            "OF High priority, SLA SNCF_TGV Premium, pièces disponibles — reprise immédiate."
        ),
        "supplier_recommendations": [],
        "overall_eta_days": 0,
        "risk_assessment": "Risque couvert — stock suffisant pour terminer l'OF.",
        "notification_text": (
            "📢 OF-2026-00201 prêt à reprendre. "
            "Reprendre à OP40_BRAKE_ASSEMBLY. BRAKE_DISC disponible (20 pcs). "
            "Priorité 1 — lancer immédiatement pour respecter le SLA."
        ),
    },
    "Critique": {
        "resume_priority": 4,
        "resume_priority_reasoning": (
            "3 pièces critiques toujours manquantes. ETA réappro estimé à 10 jours. "
            "Prioriser d'autres OF moins bloqués."
        ),
        "supplier_recommendations": [
            {
                "itemCode": "BRAKE_DISC",
                "recommended_supplier": "SUP-FAIVELEY",
                "supplier_name": "Faiveley Transport",
                "supplier_score": 91,
                "order_qty": 24,
                "unit_price_eur": 380,
                "total_price_eur": 9120,
                "estimated_lead_days": 3,
                "predicted_eta": "2026-03-14",
                "confidence": 0.92,
            },
            {
                "itemCode": "WHEELSET_920MM",
                "recommended_supplier": "SUP-GHH",
                "supplier_name": "GHH-Bonatrans",
                "supplier_score": 85,
                "order_qty": 8,
                "unit_price_eur": 8500,
                "total_price_eur": 68000,
                "estimated_lead_days": 14,
                "predicted_eta": "2026-03-25",
                "confidence": 0.78,
            },
            {
                "itemCode": "TRACTION_MOTOR_TM",
                "recommended_supplier": "SUP-ALSTOM-INT",
                "supplier_name": "Alstom Internal Supply",
                "supplier_score": 80,
                "order_qty": 10,
                "unit_price_eur": 12000,
                "total_price_eur": 120000,
                "estimated_lead_days": 10,
                "predicted_eta": "2026-03-21",
                "confidence": 0.82,
            },
        ],
        "overall_eta_days": 14,
        "risk_assessment": (
            "SLA déjà compromis. Réappro le plus lent = WHEELSET_920MM (14j via GHH-Bonatrans). "
            "Pénalités estimées : 40 000 €+."
        ),
        "notification_text": (
            "⏳ OF-2026-00202 toujours en attente. "
            "3 pièces critiques manquantes. ETA reprise estimée : 14 jours. "
            "Commandes recommandées : Faiveley (BRAKE_DISC), GHH (WHEELSET), Alstom Int. (MOTOR). "
            "Priorité 4/5 — prioriser d'autres OF."
        ),
    },
}


def get_stock_updates_preview(orders: Dict, watchlist: List[Dict]) -> List[Dict]:
    """Retourne un aperçu des mises à jour stock simulées pour chaque OF en watchlist."""
    previews = []
    for entry in watchlist:
        of_id = entry["of_id"]
        order = orders[of_id]
        scenario = order["scenario"]
        sim_stock = _SIMULATED_STOCK_AGENT2.get(scenario, {})
        original_stock = order["stock"]

        arrivals = []
        for item_code, new_qty in sim_stock.items():
            old_qty = original_stock.get(item_code, 0)
            delta = new_qty - old_qty
            if delta != 0:
                arrivals.append({
                    "itemCode": item_code,
                    "stock_avant": old_qty,
                    "stock_après": new_qty,
                    "delta": delta,
                    "type": "📦 Livraison" if delta > 0 else "⚠️ Correction",
                })

        previews.append({
            "of_id": of_id,
            "orderNumber": order["orderNumber"],
            "has_arrivals": any(a["delta"] > 0 for a in arrivals),
            "arrivals": arrivals,
        })
    return previews


def run_agent2(orders: Dict, agent1_outputs: Dict, watchlist: List[Dict]) -> List[Dict]:
    """Simule l'Agent 2 sur la watchlist. Retourne la liste des outputs Agent 2."""
    results = []
    now = datetime.now(timezone.utc).isoformat()

    for entry in watchlist:
        of_id = entry["of_id"]
        order = orders[of_id]
        scenario = order["scenario"]
        a1 = agent1_outputs.get(of_id, {})
        missing_from_a1 = a1.get("missing_components", [])

        # Stock simulé "actuel" au moment du run Agent 2
        simulated_stock = _SIMULATED_STOCK_AGENT2.get(scenario, {})
        full_stock = {**order["stock"], **simulated_stock}

        # Tracking des arrivées stock (pour affichage)
        stock_arrivals = []
        missing_codes = {mc["itemCode"] for mc in missing_from_a1}
        for item_code in missing_codes:
            old_qty = order["stock"].get(item_code, 0)
            new_qty = full_stock.get(item_code, 0)
            stock_arrivals.append({
                "itemCode": item_code,
                "stock_agent1": old_qty,
                "stock_agent2": new_qty,
                "delta": new_qty - old_qty,
            })

        # Vérifier les pénuries résolues
        resolved = []
        still_missing = []
        for mc in missing_from_a1:
            available = full_stock.get(mc["itemCode"], 0)
            if available >= mc["qtyNeeded"]:
                resolved.append({
                    "itemCode": mc["itemCode"],
                    "qtyNeeded": mc["qtyNeeded"],
                    "qtyAvailableNow": available,
                })
            else:
                still_missing.append({
                    "itemCode": mc["itemCode"],
                    "qtyNeeded": mc["qtyNeeded"],
                    "qtyAvailableNow": available,
                    "qtyStillShort": mc["qtyNeeded"] - available,
                    "isCritical": mc.get("isCritical", False),
                })

        new_status = "ReadyToResume" if len(still_missing) == 0 else "PartiallyReleased"

        ai = _SIMULATED_AI_AGENT2.get(scenario, {})

        output = {
            "of_id": of_id,
            "previous_status": order["status"],
            "new_status": new_status,
            "resolved_components": resolved,
            "still_missing_components": still_missing,
            "stock_arrivals": stock_arrivals,
            "timestamp": now,
            "ai_enhanced": True,
            "resume_priority": ai.get("resume_priority"),
            "resume_priority_reasoning": ai.get("resume_priority_reasoning", ""),
            "supplier_recommendations": ai.get("supplier_recommendations", []),
            "overall_eta_days": ai.get("overall_eta_days"),
            "risk_assessment": ai.get("risk_assessment", ""),
            "ai_notification": ai.get("notification_text", ""),
        }

        resume_op = a1.get("resume_from_operation", {})
        if new_status == "ReadyToResume" and resume_op:
            output["resume_from_operation"] = resume_op
            parts = ", ".join(f"{r['itemCode']} ({r['qtyNeeded']}/{r['qtyAvailableNow']})" for r in resolved)
            output["instruction"] = (
                f"Reprendre la production à partir de {resume_op.get('operationId', '?')}. "
                f"Composants disponibles : {parts}."
            )
        else:
            output["resume_from_operation"] = resume_op
            shortage = ", ".join(f"{sm['itemCode']} (manque {sm['qtyStillShort']})" for sm in still_missing)
            output["instruction"] = f"OF toujours en attente — composants insuffisants : {shortage}."

        # Mettre à jour le statut
        order["status"] = new_status
        order["last_agent"] = "Agent 2"

        results.append(output)

    return results


def resume_of(of_id: str, orders: Dict) -> None:
    """Passe un OF ReadyToResume en Released (reprise production)."""
    order = orders.get(of_id)
    if order and order["status"] == "ReadyToResume":
        order["status"] = "Released"
        order["last_agent"] = "Reprise"


# =============================================================================
# Scénario Custom + IA temps réel
# =============================================================================
# Les 3 scénarios ci-dessus sont SIMULÉS (outputs préconfigurés, 0 appel LLM).
# Le scénario Custom ci-dessous appelle le vrai LLM Azure AI Foundry.

BOM_FULL = [
    {"itemCode": "BOGIE_FRAME_Y32",  "description": "Châssis bogie Y32 soudé",       "qtyPerUnit": 1, "isCritical": True},
    {"itemCode": "WHEELSET_920MM",    "description": "Essieu monté roue Ø920mm",      "qtyPerUnit": 2, "isCritical": True},
    {"itemCode": "AXLE_BOX",          "description": "Boîte d'essieu",                "qtyPerUnit": 4, "isCritical": False},
    {"itemCode": "SUSPENSION_SPRING", "description": "Ressort de suspension primaire", "qtyPerUnit": 4, "isCritical": False},
    {"itemCode": "BRAKE_DISC",        "description": "Disque de frein",                "qtyPerUnit": 4, "isCritical": True},
    {"itemCode": "TRACTION_MOTOR_TM", "description": "Moteur de traction",            "qtyPerUnit": 2, "isCritical": True},
]

DEFAULT_STOCK = {
    "BOGIE_FRAME_Y32": 6,
    "WHEELSET_920MM": 10,
    "AXLE_BOX": 20,
    "SUSPENSION_SPRING": 18,
    "BRAKE_DISC": 0,
    "TRACTION_MOTOR_TM": 9,
}

HISTORICAL_OFS_DATA = [
    {"of_id": "of-2025-00087", "quantity": 2, "daysLate": 3, "wasPartialRelease": True, "blockedComponents": ["BRAKE_DISC"]},
    {"of_id": "of-2025-00112", "quantity": 4, "daysLate": 0, "wasPartialRelease": False, "blockedComponents": []},
    {"of_id": "of-2025-00148", "quantity": 6, "daysLate": 4, "wasPartialRelease": True, "blockedComponents": ["BRAKE_DISC", "TRACTION_MOTOR_TM"]},
    {"of_id": "of-2026-00015", "quantity": 3, "daysLate": 0, "wasPartialRelease": False, "blockedComponents": []},
    {"of_id": "of-2026-00058", "quantity": 4, "daysLate": 3, "wasPartialRelease": True, "blockedComponents": ["BRAKE_DISC"]},
]

MACHINE_CALENDAR_DATA = [
    {"slotId": "SLOT-2026-03-12-AM", "date": "2026-03-12", "shift": "Matin (06h-14h)",       "availableHours": 8, "currentLoad": 0.3, "status": "available"},
    {"slotId": "SLOT-2026-03-12-PM", "date": "2026-03-12", "shift": "Après-midi (14h-22h)", "availableHours": 0, "currentLoad": 1.0, "status": "maintenance"},
    {"slotId": "SLOT-2026-03-13-AM", "date": "2026-03-13", "shift": "Matin (06h-14h)",       "availableHours": 8, "currentLoad": 0.2, "status": "available"},
    {"slotId": "SLOT-2026-03-13-PM", "date": "2026-03-13", "shift": "Après-midi (14h-22h)", "availableHours": 8, "currentLoad": 0.4, "status": "available"},
    {"slotId": "SLOT-2026-03-14-AM", "date": "2026-03-14", "shift": "Matin (06h-14h)",       "availableHours": 8, "currentLoad": 0.5, "status": "available"},
]

SLA_RULES_DATA = [
    {"client": "SNCF_TGV", "serviceLevelAgreement": "Premium", "maxAcceptableDelay_days": 2, "penaltyPerDayLate_eur": 5000},
    {"client": "DEFAULT",  "serviceLevelAgreement": "Standard", "maxAcceptableDelay_days": 5, "penaltyPerDayLate_eur": 1500},
]

SUPPLIERS_DATA = [
    {"supplierId": "SUP-KNORR",     "name": "Knorr-Bremse",          "components": ["BRAKE_DISC"],        "leadTime_days": 5,  "reliability": 0.85, "unitPrice_eur": 320,   "minOrderQty": 8},
    {"supplierId": "SUP-FAIVELEY",  "name": "Faiveley Transport",    "components": ["BRAKE_DISC"],        "leadTime_days": 3,  "reliability": 0.95, "unitPrice_eur": 380,   "minOrderQty": 4},
    {"supplierId": "SUP-ALSTOM-INT","name": "Alstom Internal Supply", "components": ["TRACTION_MOTOR_TM"], "leadTime_days": 10, "reliability": 0.90, "unitPrice_eur": 12000, "minOrderQty": 1},
    {"supplierId": "SUP-GHH",       "name": "GHH-Bonatrans",         "components": ["WHEELSET_920MM"],    "leadTime_days": 14, "reliability": 0.92, "unitPrice_eur": 8500,  "minOrderQty": 2},
]

AGENT1_SYSTEM_PROMPT = """Tu es un expert en planification de production ferroviaire (Alstom).

Analyse le contexte d'un Ordre de Fabrication (OF) et fournis :
1. Un score de risque global (0-100) et un niveau de risque (HIGH / MEDIUM / LOW)
2. Une décision parmi : FULL_RELEASE, PARTIAL_RELEASE, DELAYED_RELEASE
3. Un créneau machine recommandé pour démarrer la production
4. Une explication métier détaillée en français

Critères de décision :
- FULL_RELEASE : tout est disponible, risque faible, créneau OK
- PARTIAL_RELEASE : des composants manquent mais on peut avancer partiellement
- DELAYED_RELEASE : les composants critiques manquent, le risque SLA est trop élevé

Réponds UNIQUEMENT en JSON valide avec cette structure :
{
  "decision": "FULL_RELEASE | PARTIAL_RELEASE | DELAYED_RELEASE",
  "global_risk_score": <0-100>,
  "risk_level": "HIGH | MEDIUM | LOW",
  "recommended_start_slot": "<slotId ou null>",
  "reasoning": "<explication détaillée en français>",
  "risk_factors": [
    { "factor": "<nom>", "score": <0-100>, "detail": "<detail>" }
  ],
  "estimated_production_days": <number>,
  "sla_impact": "<description impact SLA>"
}"""

AGENT2_SYSTEM_PROMPT = """Tu es un expert en gestion des approvisionnements pour l'industrie ferroviaire (Alstom).

Pour un OF partiellement lancé, analyse les pénuries et fournis :
1. Pour chaque composant manquant : le fournisseur optimal, ETA et recommandation de commande
2. Une priorité de reprise (1 = urgent, 5 = peut attendre)
3. Une notification pour le superviseur

Critères fournisseur : Fiabilité 40 %, Délai 35 %, Coût 25 %.

Réponds UNIQUEMENT en JSON valide avec cette structure :
{
  "resume_priority": <1-5>,
  "resume_priority_reasoning": "<explication>",
  "supplier_recommendations": [
    {
      "itemCode": "<composant>",
      "recommended_supplier": "<supplierId>",
      "supplier_name": "<nom>",
      "supplier_score": <0-100>,
      "order_qty": <number>,
      "unit_price_eur": <number>,
      "total_price_eur": <number>,
      "estimated_lead_days": <number>,
      "predicted_eta": "<YYYY-MM-DD>",
      "confidence": <0.0-1.0>
    }
  ],
  "notification_text": "<message pour le superviseur en français>",
  "overall_eta_days": <number>,
  "risk_assessment": "<description risque global>"
}"""


def build_live_context_agent1(
    of_data: Dict, stock: Dict, missing: List,
    mvp_decision: str, cutoff_op, last_doable,
) -> str:
    """Construit le prompt contextuel pour l'Agent 1 (même format que le vrai agent)."""
    components = BOM_FULL
    quantity = of_data["quantity"]
    missing_codes = {mc["itemCode"] for mc in missing}

    lines = [
        "# Analyse de planification OF", "",
        "## OF en cours",
        f"- ID : {of_data['of_id']}",
        f"- Produit : {of_data['productCode']}",
        f"- Quantité : {quantity}",
        f"- Priorité : {of_data['priority']}",
        f"- Échéance : {of_data['dueDate']}",
        f"- Statut actuel : Created",
        "", "## BOM — Composants",
    ]
    for comp in components:
        needed = comp["qtyPerUnit"] * quantity
        avail = stock.get(comp["itemCode"], 0)
        crit = "🔴 CRITIQUE" if comp.get("isCritical") else "⚪"
        icon = "✅" if avail >= needed else "❌"
        lines.append(f"- {icon} {comp['itemCode']} ({crit}) — besoin {needed}, dispo {avail}")

    lines += ["", "## Gamme de fabrication"]
    for op in ROUTING:
        blocked = set(op.get("requiredComponents", [])) & missing_codes
        icon = "🔴 BLOQUÉ" if blocked else "🟢 OK"
        lines.append(f"- séq.{op['sequence']} {op['operationId']} — {icon}")

    lines += ["", "## Décision MVP (déterministe)", f"- Décision : {mvp_decision}"]
    if cutoff_op:
        lines.append(f"- Coupure à : {cutoff_op['operationId']} (séq. {cutoff_op['sequence']})")
    if last_doable:
        lines.append(f"- Dernière op réalisable : {last_doable['operationId']}")

    if missing:
        lines += ["", "## Composants manquants"]
        for mc in missing:
            flag = " ⚠️ CRITIQUE" if mc.get("isCritical") else ""
            lines.append(f"- {mc['itemCode']}{flag} — manque {mc['qtyShortage']} (besoin {mc['qtyNeeded']}, dispo {mc['qtyAvailable']})")

    lines += ["", "## Historique des OF similaires"]
    for rec in HISTORICAL_OFS_DATA:
        late = f"{rec['daysLate']}j retard" if rec["daysLate"] > 0 else "à l'heure"
        mode = "partiel" if rec["wasPartialRelease"] else "complet"
        blk = f", bloqué par {rec['blockedComponents']}" if rec["blockedComponents"] else ""
        lines.append(f"- {rec['of_id']} — qty {rec['quantity']}, {mode}, {late}{blk}")

    lines += ["", "## Créneaux machine disponibles"]
    for slot in MACHINE_CALENDAR_DATA:
        if slot["status"] == "available":
            lines.append(f"- {slot['slotId']} — {slot['date']} {slot['shift']} — charge {slot['currentLoad']*100:.0f}% — {slot['availableHours']}h dispo")

    lines += ["", "## Règles SLA"]
    for rule in SLA_RULES_DATA:
        lines.append(f"- Client {rule['client']} ({rule['serviceLevelAgreement']}) — retard max {rule['maxAcceptableDelay_days']}j, pénalité {rule['penaltyPerDayLate_eur']}€/j")

    return "\n".join(lines)


def build_live_context_agent2(
    of_id: str, of_priority: str, of_due_date: str,
    agent1_state: Dict, stock: Dict,
    still_missing: List, resolved: List,
) -> str:
    """Construit le prompt contextuel pour l'Agent 2."""
    lines = [
        "# Analyse de réapprovisionnement pour OF partiel", "",
        "## OF concerné",
        f"- ID : {of_id}",
        f"- Priorité : {of_priority}",
        f"- Échéance : {of_due_date}",
        f"- Décision Agent 1 : {agent1_state.get('decision', 'N/A')}",
    ]
    if agent1_state.get("ai_enhanced"):
        lines.append(f"- Score risque Agent 1 : {agent1_state.get('global_risk_score', '?')}/100")
    resume_op = agent1_state.get("resume_from_operation", {})
    if resume_op:
        lines.append(f"- Reprendre à : {resume_op.get('operationId', '?')}")

    if resolved:
        lines += ["", "## Composants revenus en stock ✅"]
        for r in resolved:
            lines.append(f"- {r['itemCode']} — dispo {r['qtyAvailableNow']} ≥ besoin {r['qtyNeeded']}")

    if still_missing:
        lines += ["", "## Composants toujours manquants ❌"]
        for sm in still_missing:
            crit = " ⚠️ CRITIQUE" if sm.get("isCritical") else ""
            lines.append(f"- {sm['itemCode']}{crit} — besoin {sm['qtyNeeded']}, dispo {sm['qtyAvailableNow']}, manque {sm['qtyStillShort']}")

        missing_codes = {sm["itemCode"] for sm in still_missing}
        lines += ["", "## Fournisseurs disponibles"]
        for sup in SUPPLIERS_DATA:
            relevant = set(sup.get("components", [])) & missing_codes
            if relevant:
                lines.append(f"### {sup['name']} ({sup['supplierId']})")
                lines.append(f"- Composants : {', '.join(relevant)}")
                lines.append(f"- Lead time : {sup['leadTime_days']} jours")
                lines.append(f"- Fiabilité : {sup['reliability']*100:.0f}%")
                lines.append(f"- Prix unitaire : {sup['unitPrice_eur']}€")
                lines.append(f"- Qté min commande : {sup['minOrderQty']}")

    lines += ["", "## Contraintes SLA"]
    for rule in SLA_RULES_DATA:
        lines.append(f"- Client {rule['client']} ({rule['serviceLevelAgreement']}) — retard max {rule['maxAcceptableDelay_days']}j, pénalité {rule['penaltyPerDayLate_eur']}€/j")

    return "\n".join(lines)


def _extract_json_from_response(response: str) -> Optional[Dict]:
    """Extrait le JSON d'une réponse LLM."""
    try:
        if "```json" in response:
            start = response.index("```json") + 7
            end = response.index("```", start)
            return json.loads(response[start:end].strip())
        start = response.find("{")
        if start >= 0:
            end = response.rfind("}")
            return json.loads(response[start:end + 1])
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def call_llm(instructions: str, context: str):
    """Appel synchrone au LLM Azure AI Foundry.

    Returns: (parsed_json | None, raw_text, error_msg | None)
    """
    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT") or os.getenv("AI_FOUNDRY_PROJECT_ENDPOINT")
    model = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4.1")

    if not endpoint:
        return None, "", "Variable AZURE_AI_PROJECT_ENDPOINT non définie."

    try:
        from azure.ai.projects import AIProjectClient
        from azure.identity import DefaultAzureCredential
    except ImportError:
        return None, "", "Packages azure-ai-projects / azure-identity non installés."

    try:
        client = AIProjectClient(
            endpoint=endpoint,
            credential=DefaultAzureCredential(),
        )
        response = client.inference.get_chat_completions_client().complete(
            model=model,
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": context},
            ],
        )
        raw_text = response.choices[0].message.content
        parsed = _extract_json_from_response(raw_text)
        return parsed, raw_text, None
    except Exception as e:
        return None, "", f"{type(e).__name__}: {e}"
