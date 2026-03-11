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
