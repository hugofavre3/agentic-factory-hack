"""Seed data et logique simulée — Maestro & Sentinelle.

Cadrage : Anticiper les risques de blocage et de retard AVANT qu'ils n'arrivent.
Maestro regarde en avance le film de production.
Sentinelle surveille les hypothèses prises par Maestro.

Contient :
  - Les 3 scénarios (OK / Moyen / Critique) avec cadrage anticipation des retards
  - run_maestro, run_sentinelle, run_orchestrator
  - Données de référence (BOM, routing avec timing, fournisseurs, etc.)
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import copy
import json
import os


# =============================================================================
# Gamme de fabrication avec timing (heures)
# =============================================================================

ROUTING = [
    {
        "operationId": "OP10_FRAME_PREP",
        "sequence": 10,
        "description": "Préparation châssis",
        "requiredComponents": ["BOGIE_FRAME_Y32"],
        "duration_hours": 4,
        "cumulative_start_hours": 0,
        "cumulative_end_hours": 4,
    },
    {
        "operationId": "OP20_WHEELSET_MOUNT",
        "sequence": 20,
        "description": "Montage essieux + boîtes",
        "requiredComponents": ["WHEELSET_920MM", "AXLE_BOX"],
        "duration_hours": 8,
        "cumulative_start_hours": 4,
        "cumulative_end_hours": 12,
    },
    {
        "operationId": "OP30_SUSPENSION",
        "sequence": 30,
        "description": "Installation suspension",
        "requiredComponents": ["SUSPENSION_SPRING"],
        "duration_hours": 6,
        "cumulative_start_hours": 12,
        "cumulative_end_hours": 18,
    },
    {
        "operationId": "OP40_BRAKE_ASSEMBLY",
        "sequence": 40,
        "description": "Montage freins",
        "requiredComponents": ["BRAKE_DISC"],
        "duration_hours": 8,
        "cumulative_start_hours": 18,
        "cumulative_end_hours": 26,
    },
    {
        "operationId": "OP50_TRACTION_MOTOR",
        "sequence": 50,
        "description": "Installation moteur traction",
        "requiredComponents": ["TRACTION_MOTOR_TM"],
        "duration_hours": 8,
        "cumulative_start_hours": 26,
        "cumulative_end_hours": 34,
    },
    {
        "operationId": "OP60_TESTING",
        "sequence": 60,
        "description": "Tests et contrôle qualité",
        "requiredComponents": [],
        "duration_hours": 6,
        "cumulative_start_hours": 34,
        "cumulative_end_hours": 40,
    },
]

WORK_HOURS_PER_DAY = 8  # 8h utiles par jour ouvré


# =============================================================================
# BOM — Nomenclature
# =============================================================================

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


# =============================================================================
# Fournisseurs
# =============================================================================

SUPPLIERS_DATA = [
    {"supplierId": "SUP-KNORR",      "name": "Knorr-Bremse",          "email": "commercial@knorr-bremse.com",  "components": ["BRAKE_DISC"],        "leadTime_days": 5,  "reliability": 0.85, "unitPrice_eur": 320,   "minOrderQty": 8},
    {"supplierId": "SUP-FAIVELEY",   "name": "Faiveley Transport",    "email": "commandes@faiveley.com",       "components": ["BRAKE_DISC"],        "leadTime_days": 3,  "reliability": 0.95, "unitPrice_eur": 380,   "minOrderQty": 4},
    {"supplierId": "SUP-ALSTOM-INT", "name": "Alstom Internal Supply", "email": "supply.internal@alstom.com",  "components": ["TRACTION_MOTOR_TM"], "leadTime_days": 10, "reliability": 0.90, "unitPrice_eur": 12000, "minOrderQty": 1},
    {"supplierId": "SUP-GHH",        "name": "GHH-Bonatrans",         "email": "orders@ghh-bonatrans.com",     "components": ["WHEELSET_920MM"],    "leadTime_days": 14, "reliability": 0.92, "unitPrice_eur": 8500,  "minOrderQty": 2},
]

HISTORICAL_OFS_DATA = [
    {"of_id": "of-2025-00087", "quantity": 2, "daysLate": 3, "wasPartialRelease": True,  "blockedComponents": ["BRAKE_DISC"],                        "blockedAtStep": "OP40"},
    {"of_id": "of-2025-00112", "quantity": 4, "daysLate": 0, "wasPartialRelease": False, "blockedComponents": [],                                     "blockedAtStep": None},
    {"of_id": "of-2025-00148", "quantity": 6, "daysLate": 4, "wasPartialRelease": True,  "blockedComponents": ["BRAKE_DISC", "TRACTION_MOTOR_TM"],   "blockedAtStep": "OP40"},
    {"of_id": "of-2026-00015", "quantity": 3, "daysLate": 0, "wasPartialRelease": False, "blockedComponents": [],                                     "blockedAtStep": None},
    {"of_id": "of-2026-00058", "quantity": 4, "daysLate": 3, "wasPartialRelease": True,  "blockedComponents": ["BRAKE_DISC"],                        "blockedAtStep": "OP40"},
]

MACHINE_CALENDAR_DATA = [
    {"slotId": "SLOT-2026-03-12-AM", "date": "2026-03-12", "shift": "Matin (06h–14h)",       "availableHours": 8, "currentLoad": 0.30, "status": "available"},
    {"slotId": "SLOT-2026-03-12-PM", "date": "2026-03-12", "shift": "Après-midi (14h–22h)", "availableHours": 0, "currentLoad": 1.00, "status": "maintenance"},
    {"slotId": "SLOT-2026-03-13-AM", "date": "2026-03-13", "shift": "Matin (06h–14h)",       "availableHours": 8, "currentLoad": 0.20, "status": "available"},
    {"slotId": "SLOT-2026-03-13-PM", "date": "2026-03-13", "shift": "Après-midi (14h–22h)", "availableHours": 8, "currentLoad": 0.40, "status": "available"},
    {"slotId": "SLOT-2026-03-14-AM", "date": "2026-03-14", "shift": "Matin (06h–14h)",       "availableHours": 8, "currentLoad": 0.50, "status": "available"},
    {"slotId": "SLOT-2026-03-14-PM", "date": "2026-03-14", "shift": "Après-midi (14h–22h)", "availableHours": 8, "currentLoad": 0.35, "status": "available"},
    {"slotId": "SLOT-2026-03-17-AM", "date": "2026-03-17", "shift": "Matin (06h–14h)",       "availableHours": 8, "currentLoad": 0.60, "status": "available"},
    {"slotId": "SLOT-2026-03-26-AM", "date": "2026-03-26", "shift": "Matin (06h–14h)",       "availableHours": 8, "currentLoad": 0.10, "status": "available"},
]

SLA_RULES_DATA = [
    {"client": "SNCF_TGV", "serviceLevelAgreement": "Premium", "maxAcceptableDelay_days": 2, "penaltyPerDayLate_eur": 5000},
    {"client": "DEFAULT",  "serviceLevelAgreement": "Standard", "maxAcceptableDelay_days": 5, "penaltyPerDayLate_eur": 1500},
]


# =============================================================================
# Seed data — 3 scénarios
# =============================================================================

def build_seed_orders() -> Dict[str, Dict]:
    """Retourne les 3 OF de démonstration indexés par of_id."""
    return {
        # ── Scénario OK ──────────────────────────────────────────
        "of-2026-00200": {
            "of_id": "of-2026-00200",
            "scenario": "OK",
            "scenario_label": "✅ Scénario OK — Stock suffisant, aucun risque",
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
        # ── Scénario Moyen ──────────────────────────────────────
        "of-2026-00201": {
            "of_id": "of-2026-00201",
            "scenario": "Moyen",
            "scenario_label": "⚠️ Scénario Moyen — Pièce manquante, ETA serrée",
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
        # ── Scénario Critique ───────────────────────────────────
        "of-2026-00202": {
            "of_id": "of-2026-00202",
            "scenario": "Critique",
            "scenario_label": "🛑 Scénario Critique — Risque majeur de blocage",
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


# =============================================================================
# Helpers — analyse de production
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


def _find_risk_steps(missing_components):
    """Pour chaque composant manquant, trouve l'étape qui le consomme et le temps pour y arriver."""
    risk_steps = []
    missing_codes = {mc["itemCode"] for mc in missing_components}
    for op in ROUTING:
        blocked_items = set(op.get("requiredComponents", [])) & missing_codes
        if blocked_items:
            for item in blocked_items:
                mc = next(m for m in missing_components if m["itemCode"] == item)
                risk_steps.append({
                    "itemCode": item,
                    "operationId": op["operationId"],
                    "sequence": op["sequence"],
                    "description": op["description"],
                    "time_to_reach_hours": op["cumulative_start_hours"],
                    "time_to_reach_days": round(op["cumulative_start_hours"] / WORK_HOURS_PER_DAY, 1),
                    "qtyShortage": mc["qtyShortage"],
                    "isCritical": mc.get("isCritical", False),
                })
    return risk_steps


def _build_simulated_email(supplier, item_code, qty, of_number, risk_step_op, delivery_date):
    """Construit un email fournisseur simulé."""
    return {
        "to": f"{supplier['email']}",
        "to_name": supplier["name"],
        "supplier_id": supplier["supplierId"],
        "subject": f"[URGENT] Commande {item_code} × {qty} — {of_number}",
        "body": (
            f"Bonjour,\n\n"
            f"Dans le cadre de l'{of_number}, nous avons un besoin urgent de "
            f"{qty} unité(s) de {item_code}.\n\n"
            f"Stock actuel : 0 / Besoin : {qty}\n"
            f"Date de livraison souhaitée : {delivery_date}\n"
            f"Impact si retard : blocage à l'étape {risk_step_op}\n\n"
            f"Merci de confirmer disponibilité et délai de livraison.\n\n"
            f"Cordialement,\n"
            f"Système Maestro — Planification IA Alstom"
        ),
    }


# =============================================================================
# Maestro — Outputs simulés par scénario
# =============================================================================

_SIMULATED_MAESTRO = {
    "OK": {
        "risk_level": "VERT",
        "global_risk_score": 8,
        "recommended_action": "LANCER_IMMEDIAT",
        "recommended_launch_date": "2026-03-12",
        "recommended_launch_slot": "SLOT-2026-03-12-AM",
        "estimated_production_days": 5,
        # ── Risque retard ──
        "probabilite_blocage_pct": 0,
        "estimated_delay_days": 0,
        "estimated_penalty_eur": 0,
        "etape_a_risque": None,
        # ── Messages ──
        "maestro_message": (
            "Tous les composants sont disponibles en quantité suffisante pour l'ensemble de la gamme. "
            "Aucun risque de blocage à aucune étape. Pas de retard attendu, on lance comme prévu."
        ),
        "reasoning": (
            "Stock complet vérifié sur les 6 composants. Marge confortable de ~27 jours avant "
            "échéance. L'historique ne montre aucun blocage récent sur ce type d'OF. "
            "Le créneau du 12/03 matin est disponible (charge 30 %). "
            "Recommandation : lancer la production immédiatement."
        ),
        "risk_factors": [
            {"factor": "Stock",      "score": 5,  "detail": "Tous composants disponibles"},
            {"factor": "Historique", "score": 10, "detail": "Aucun retard récent"},
            {"factor": "Échéance",   "score": 5,  "detail": "27 jours de marge"},
            {"factor": "Planning",   "score": 15, "detail": "Créneaux dégagés"},
        ],
        "supplier_order_plan": [],
        "simulated_emails": [],
        "rescheduling_options": [],
        "sla_impact": "Aucun risque SLA — livraison bien avant l'échéance.",
    },
    "Moyen": {
        "risk_level": "ORANGE",
        "global_risk_score": 55,
        "recommended_action": "LANCER_DECALE",
        "recommended_launch_date": "2026-03-13",
        "recommended_launch_slot": "SLOT-2026-03-13-AM",
        "estimated_production_days": 5,
        # ── Risque retard ──
        "probabilite_blocage_pct": 30,
        "estimated_delay_days": 0,
        "estimated_penalty_eur": 0,
        "etape_a_risque": {
            "operationId": "OP40_BRAKE_ASSEMBLY",
            "sequence": 40,
            "description": "Montage freins",
            "time_to_reach_days": 2.25,
            "composant_manquant": "BRAKE_DISC",
        },
        # ── Messages ──
        "maestro_message": (
            "Le composant BRAKE_DISC est absent du stock. Il est consommé à l'étape OP40 "
            "(Montage freins), que la production atteindra au bout de ~2,25 jours. "
            "Le fournisseur Faiveley Transport peut livrer sous 3 jours. "
            "Si on lance demain matin (13/03), la production atteindra OP40 le 15/03 après-midi, "
            "et les freins seront livrés le 15/03 au plus tard. C'est serré mais réaliste. "
            "Garde un œil sur la confirmation fournisseur."
        ),
        "reasoning": (
            "BRAKE_DISC manquant (besoin 16, stock 0). Consommé à OP40 (séq. 40), "
            "étape atteinte en 18h de production soit ~2,25 jours ouvrés. "
            "Meilleur fournisseur : Faiveley Transport (fiabilité 95 %, délai 3 j). "
            "Si lancement immédiat → arrive à OP40 le 14/03 après-midi, freins livrés le 15/03 → "
            "0,5 j d'attente potentielle. Si lancement décalé au 13/03 matin → arrive à OP40 le "
            "15/03 après-midi, freins livrés le 15/03 → timing aligné. "
            "Historique : 3-4 j de retard sur OF similaires bloqués par BRAKE_DISC."
        ),
        "risk_factors": [
            {"factor": "Composant critique manquant", "score": 75, "detail": "BRAKE_DISC absent, consommé à OP40"},
            {"factor": "Timing pièce vs étape",       "score": 50, "detail": "ETA fournisseur (3j) ≈ temps d'arrivée à OP40 (2,25j)"},
            {"factor": "Historique retards",            "score": 55, "detail": "3-4 j retard historique sur BRAKE_DISC"},
            {"factor": "Échéance / SLA",                "score": 40, "detail": "13 j restants, pénalité 5 000 €/j au-delà de +2 j"},
        ],
        "supplier_order_plan": [
            {
                "itemCode": "BRAKE_DISC",
                "recommended_supplier": "SUP-FAIVELEY",
                "supplier_name": "Faiveley Transport",
                "order_qty": 16,
                "unit_price_eur": 380,
                "total_price_eur": 6080,
                "estimated_lead_days": 3,
                "order_date": "2026-03-12",
                "predicted_eta": "2026-03-15",
                "confidence": 0.92,
            },
        ],
        "simulated_emails": [
            {
                "to": "commandes@faiveley.com",
                "to_name": "Faiveley Transport",
                "supplier_id": "SUP-FAIVELEY",
                "subject": "[URGENT] Commande BRAKE_DISC × 16 — OF-2026-00201",
                "body": (
                    "Bonjour,\n\n"
                    "Dans le cadre de l'OF-2026-00201 (4 bogies Y32), nous avons un besoin "
                    "urgent de 16 disques de frein (BRAKE_DISC).\n\n"
                    "Stock actuel : 0 / Besoin : 16\n"
                    "Date de livraison souhaitée : 15/03/2026\n"
                    "Impact si retard : blocage à l'étape OP40 (Montage freins)\n\n"
                    "Merci de confirmer disponibilité et délai de livraison.\n\n"
                    "Cordialement,\n"
                    "Système Maestro — Planification IA Alstom"
                ),
            },
        ],
        "rescheduling_options": [],
        "sla_impact": (
            "Si les BRAKE_DISC arrivent sous 3 jours, l'OF reste dans le SLA. "
            "Au-delà, pénalité de 5 000 €/jour."
        ),
    },
    "Critique": {
        "risk_level": "ROUGE",
        "global_risk_score": 92,
        "recommended_action": "REPORTER_ET_REPLANIFIER",
        "recommended_launch_date": None,
        "recommended_launch_slot": None,
        "estimated_production_days": 5,
        # ── Risque retard ──
        "probabilite_blocage_pct": 95,
        "estimated_delay_days": 10,
        "estimated_penalty_eur": 50000,
        "etape_a_risque": {
            "operationId": "OP20_WHEELSET_MOUNT",
            "sequence": 20,
            "description": "Montage essieux + boîtes",
            "time_to_reach_days": 0.5,
            "composant_manquant": "WHEELSET_920MM",
        },
        # ── Messages ──
        "maestro_message": (
            "3 composants critiques manquants : WHEELSET_920MM, BRAKE_DISC, TRACTION_MOTOR_TM. "
            "Le premier blocage (WHEELSET) apparaît à OP20, atteint en seulement 4h (0,5 jour). "
            "Le fournisseur le plus rapide pour les WHEELSET (GHH-Bonatrans) a un délai de 14 jours. "
            "Dans toutes les hypothèses réalistes, la production sera bloquée quasi immédiatement. "
            "Ne pas lancer maintenant. Deux créneaux de reprogrammation sont proposés."
        ),
        "reasoning": (
            "3 composants critiques absents :\n"
            "• WHEELSET_920MM — besoin 12, dispo 4, manque 8 → bloque OP20 (atteint en 0,5 j)\n"
            "• BRAKE_DISC — besoin 24, dispo 0, manque 24 → bloque OP40 (atteint en 2,25 j)\n"
            "• TRACTION_MOTOR_TM — besoin 12, dispo 2, manque 10 → bloque OP50 (atteint en 3,25 j)\n"
            "Réappro le plus lent : WHEELSET_920MM (14 j via GHH-Bonatrans). "
            "Échéance dans 8 jours : retard quasi certain de 8-10 jours. "
            "Pénalités estimées : 5 000 €/j × 10 j = 50 000 €."
        ),
        "risk_factors": [
            {"factor": "Composants critiques manquants",  "score": 95, "detail": "3 pièces critiques absentes"},
            {"factor": "Timing pièce vs étape",           "score": 98, "detail": "OP20 atteint en 0,5 j, pièces livrées en 14 j"},
            {"factor": "Historique retards",               "score": 85, "detail": "7 j attente stock historique"},
            {"factor": "Échéance / SLA",                   "score": 95, "detail": "8 j restants, réappro 14 j — retard certain"},
        ],
        "supplier_order_plan": [
            {
                "itemCode": "BRAKE_DISC",
                "recommended_supplier": "SUP-FAIVELEY",
                "supplier_name": "Faiveley Transport",
                "order_qty": 24,
                "unit_price_eur": 380,
                "total_price_eur": 9120,
                "estimated_lead_days": 3,
                "order_date": "2026-03-12",
                "predicted_eta": "2026-03-15",
                "confidence": 0.92,
            },
            {
                "itemCode": "WHEELSET_920MM",
                "recommended_supplier": "SUP-GHH",
                "supplier_name": "GHH-Bonatrans",
                "order_qty": 8,
                "unit_price_eur": 8500,
                "total_price_eur": 68000,
                "estimated_lead_days": 14,
                "order_date": "2026-03-12",
                "predicted_eta": "2026-03-26",
                "confidence": 0.78,
            },
            {
                "itemCode": "TRACTION_MOTOR_TM",
                "recommended_supplier": "SUP-ALSTOM-INT",
                "supplier_name": "Alstom Internal Supply",
                "order_qty": 10,
                "unit_price_eur": 12000,
                "total_price_eur": 120000,
                "estimated_lead_days": 10,
                "order_date": "2026-03-12",
                "predicted_eta": "2026-03-22",
                "confidence": 0.82,
            },
        ],
        "simulated_emails": [
            {
                "to": "orders@ghh-bonatrans.com",
                "to_name": "GHH-Bonatrans",
                "supplier_id": "SUP-GHH",
                "subject": "[URGENT] Commande WHEELSET_920MM × 8 — OF-2026-00202",
                "body": (
                    "Bonjour,\n\n"
                    "Dans le cadre de l'OF-2026-00202 (6 bogies Y32), nous avons un besoin "
                    "urgent de 8 essieux montés (WHEELSET_920MM).\n\n"
                    "Stock actuel : 4 / Besoin : 12\n"
                    "Date de livraison souhaitée : 26/03/2026\n"
                    "Impact si retard : blocage à l'étape OP20 (Montage essieux)\n\n"
                    "Merci de confirmer disponibilité et délai de livraison.\n\n"
                    "Cordialement,\n"
                    "Système Maestro — Planification IA Alstom"
                ),
            },
            {
                "to": "commandes@faiveley.com",
                "to_name": "Faiveley Transport",
                "supplier_id": "SUP-FAIVELEY",
                "subject": "[URGENT] Commande BRAKE_DISC × 24 — OF-2026-00202",
                "body": (
                    "Bonjour,\n\n"
                    "Dans le cadre de l'OF-2026-00202 (6 bogies Y32), nous avons un besoin "
                    "urgent de 24 disques de frein (BRAKE_DISC).\n\n"
                    "Stock actuel : 0 / Besoin : 24\n"
                    "Date de livraison souhaitée : 15/03/2026\n"
                    "Impact si retard : blocage à l'étape OP40 (Montage freins)\n\n"
                    "Merci de confirmer disponibilité et délai de livraison.\n\n"
                    "Cordialement,\n"
                    "Système Maestro — Planification IA Alstom"
                ),
            },
            {
                "to": "supply.internal@alstom.com",
                "to_name": "Alstom Internal Supply",
                "supplier_id": "SUP-ALSTOM-INT",
                "subject": "[URGENT] Commande TRACTION_MOTOR_TM × 10 — OF-2026-00202",
                "body": (
                    "Bonjour,\n\n"
                    "Dans le cadre de l'OF-2026-00202 (6 bogies Y32), nous avons un besoin "
                    "urgent de 10 moteurs de traction (TRACTION_MOTOR_TM).\n\n"
                    "Stock actuel : 2 / Besoin : 12\n"
                    "Date de livraison souhaitée : 22/03/2026\n"
                    "Impact si retard : blocage à l'étape OP50 (Moteur traction)\n\n"
                    "Merci de confirmer disponibilité et délai de livraison.\n\n"
                    "Cordialement,\n"
                    "Système Maestro — Planification IA Alstom"
                ),
            },
        ],
        "rescheduling_options": [
            {
                "label": "Créneau A — Lancer le 26/03 matin",
                "slot": "SLOT-2026-03-26-AM",
                "launch_date": "2026-03-26",
                "estimated_completion": "2026-03-31",
                "delay_client_days": 11,
                "penalty_eur": 55000,
                "comment": "Toutes les pièces disponibles. Retard de 11 jours.",
            },
            {
                "label": "Créneau B — Lancer le 22/03 (risque partiel)",
                "slot": "SLOT-2026-03-22-AM",
                "launch_date": "2026-03-22",
                "estimated_completion": "2026-03-28",
                "delay_client_days": 8,
                "penalty_eur": 40000,
                "comment": (
                    "BRAKE_DISC et MOTOR disponibles, WHEELSET attendu le 26/03. "
                    "Risque de blocage à OP20 le 22/03 si WHEELSET en retard."
                ),
            },
        ],
        "sla_impact": (
            "SLA compromis — échéance 20/03, réappro complet estimé à 14 jours. "
            "Pénalités : 5 000 €/jour × 10+ jours = 50 000 €+."
        ),
    },
}


# =============================================================================
# Maestro — run
# =============================================================================

def run_maestro(of_id: str, orders: Dict) -> Dict:
    """Maestro analyse l'OF et produit une recommandation de lancement."""
    order = orders[of_id]
    scenario = order["scenario"]
    components = order["components"]
    quantity = order["quantity"]
    stock = order["stock"]

    # --- Analyse déterministe ---
    missing = _check_availability(components, quantity, stock)
    cutoff_op = _find_cutoff(ROUTING, missing)
    last_doable = _find_last_doable(ROUTING, cutoff_op)
    risk_steps = _find_risk_steps(missing)

    # --- IA simulée ---
    ai = _SIMULATED_MAESTRO[scenario]

    # Jours avant échéance
    due_date = datetime.fromisoformat(order["dueDate"].replace("Z", "+00:00"))
    now_dt = datetime.now(timezone.utc)
    days_until_due = (due_date - now_dt).days

    now = now_dt.isoformat()
    output = {
        "of_id": of_id,
        "orderNumber": order["orderNumber"],
        "productCode": order["productCode"],
        "quantity": quantity,
        "timestamp": now,
        # ── Risque ──
        "risk_level": ai["risk_level"],
        "global_risk_score": ai["global_risk_score"],
        "probabilite_blocage_pct": ai["probabilite_blocage_pct"],
        "etape_a_risque": ai["etape_a_risque"],
        "risk_steps": risk_steps,
        # ── Lancement ──
        "recommended_action": ai["recommended_action"],
        "recommended_launch_date": ai["recommended_launch_date"],
        "recommended_launch_slot": ai["recommended_launch_slot"],
        "estimated_production_days": ai["estimated_production_days"],
        # ── Retard ──
        "days_until_due": days_until_due,
        "estimated_delay_days": ai["estimated_delay_days"],
        "estimated_penalty_eur": ai["estimated_penalty_eur"],
        # ── Messages ──
        "maestro_message": ai["maestro_message"],
        "reasoning": ai["reasoning"],
        "risk_factors": ai["risk_factors"],
        "sla_impact": ai["sla_impact"],
        # ── Plan fournisseur ──
        "supplier_order_plan": ai["supplier_order_plan"],
        "simulated_emails": ai["simulated_emails"],
        # ── Reprogrammation (si critique) ──
        "rescheduling_options": ai["rescheduling_options"],
        # ── Composants ──
        "missing_components": missing,
        "cutoff_operation": {
            "operationId": cutoff_op["operationId"],
            "sequence": cutoff_op["sequence"],
            "description": cutoff_op["description"],
        } if cutoff_op else None,
        # ── Statut interne ──
        "operator_decision": None,
        "previous_status": order["status"],
    }

    # Status intermédiaire : en attente de décision
    output["new_status"] = "AwaitingDecision"
    order["status"] = "AwaitingDecision"
    order["last_agent"] = "Maestro"

    return output


# =============================================================================
# Décision opérateur
# =============================================================================

def apply_operator_decision(of_id: str, orders: Dict, maestro_outputs: Dict,
                            decision: str) -> str:
    """Applique la décision de l'opérateur sur un OF analysé par Maestro."""
    order = orders[of_id]
    output = maestro_outputs[of_id]
    output["operator_decision"] = decision

    status_map = {
        "LANCER_IMMEDIAT": "Released",
        "LANCER_DECALE": "EnSurveillance",
        "REPORTER_ET_REPLANIFIER": "Replanifie",
    }
    new_status = status_map.get(decision, "AwaitingDecision")
    output["new_status"] = new_status
    order["status"] = new_status
    order["last_agent"] = "Opérateur"

    missing = output.get("missing_components", [])

    if decision == "LANCER_IMMEDIAT":
        if not missing:
            instruction = "Production complète — tous les composants sont disponibles. Lancer immédiatement."
        else:
            shortage = ", ".join(f"{mc['itemCode']} (manque {mc['qtyShortage']})" for mc in missing)
            instruction = (
                f"⚠️ Lancement immédiat sur décision opérateur malgré composants manquants : {shortage}. "
                f"Risque de blocage en production."
            )
    elif decision == "LANCER_DECALE":
        slot = output.get("recommended_launch_slot", "?")
        date_str = output.get("recommended_launch_date", "?")
        shortage = ", ".join(mc["itemCode"] for mc in missing) if missing else "—"
        instruction = (
            f"Lancement prévu le {date_str} (créneau {slot}). "
            f"Surveiller l'arrivée de : {shortage}. "
            f"Sentinelle activée pour suivi en continu."
        )
    else:  # REPORTER_ET_REPLANIFIER
        options = output.get("rescheduling_options", [])
        if options:
            opt = options[0]
            instruction = (
                f"OF reporté. Créneau de reprogrammation proposé : {opt['label']}. "
                f"Retard client estimé : +{opt['delay_client_days']} jours. "
                f"Sentinelle activée pour suivi fournisseurs."
            )
        else:
            critical = [mc["itemCode"] for mc in missing if mc.get("isCritical")]
            instruction = (
                f"OF reporté — composants critiques manquants : {', '.join(critical) if critical else 'N/A'}. "
                f"En attente de reprogrammation."
            )

    output["instruction"] = instruction
    return instruction


# =============================================================================
# Orchestrateur
# =============================================================================

def run_orchestrator(maestro_outputs: Dict) -> List[Dict]:
    """Scanne les outputs Maestro et retourne la watchlist pour Sentinelle."""
    watchlist = []
    for of_id, output in maestro_outputs.items():
        op_decision = output.get("operator_decision")
        if op_decision in ("LANCER_DECALE", "REPORTER_ET_REPLANIFIER"):
            watchlist.append({
                "of_id": of_id,
                "status": output["new_status"],
                "productCode": output["productCode"],
                "decision": op_decision,
                "risk_level": output.get("risk_level", "?"),
                "days_until_due": output.get("days_until_due", "?"),
                "etape_a_risque": output.get("etape_a_risque", {}).get("operationId", "—") if output.get("etape_a_risque") else "—",
            })
    return watchlist


# =============================================================================
# Sentinelle — Outputs simulés
# =============================================================================

_SIMULATED_STOCK_SENTINELLE = {
    "Moyen": {
        "BRAKE_DISC": 20,  # Livraison reçue
    },
    "Critique": {
        "WHEELSET_920MM": 4,
        "BRAKE_DISC": 0,
        "TRACTION_MOTOR_TM": 2,
    },
}

_SIMULATED_SENTINELLE = {
    "Moyen": {
        "initial_risk_level": "ORANGE",
        "current_risk_level": "VERT",
        "risk_evolution": "BAISSE",
        "warning_status": "LEVE",
        "sentinelle_message": (
            "Bonne nouvelle : les BRAKE_DISC ont été reçus (20 unités, livraison Faiveley confirmée). "
            "Le risque de blocage à l'étape OP40 est désormais levé. "
            "La production peut se poursuivre normalement jusqu'à la fin de la gamme."
        ),
        "parts_tracking": [
            {
                "itemCode": "BRAKE_DISC",
                "initial_status": "MANQUANT",
                "current_status": "REÇU",
                "supplier": "Faiveley Transport",
                "eta_initial": "2026-03-15",
                "eta_updated": "2026-03-14",
                "qty_received": 20,
            },
        ],
        "updated_eta_end": "2026-03-18",
        "updated_delay_days": 0,
        "resume_priority": 1,
        "resume_priority_reasoning": "Pièces disponibles, aucun risque résiduel. Reprise immédiate recommandée.",
        "plan_b_needed": False,
        "rescheduling_proposal": None,
        "supplier_recommendations": [],
    },
    "Critique": {
        "initial_risk_level": "ROUGE",
        "current_risk_level": "ROUGE",
        "risk_evolution": "STABLE",
        "warning_status": "CONFIRME",
        "sentinelle_message": (
            "Aucune amélioration : les 3 composants critiques sont toujours manquants. "
            "Le risque de blocage est confirmé. "
            "WHEELSET_920MM attendu le 26/03 (GHH-Bonatrans), "
            "TRACTION_MOTOR_TM attendu le 22/03 (Alstom Internal), "
            "BRAKE_DISC attendu le 15/03 (Faiveley). "
            "Retard client confirmé : +10 jours minimum."
        ),
        "parts_tracking": [
            {
                "itemCode": "WHEELSET_920MM",
                "initial_status": "MANQUANT",
                "current_status": "EN_ATTENTE",
                "supplier": "GHH-Bonatrans",
                "eta_initial": "2026-03-26",
                "eta_updated": "2026-03-26",
                "qty_received": 0,
            },
            {
                "itemCode": "BRAKE_DISC",
                "initial_status": "MANQUANT",
                "current_status": "EN_ATTENTE",
                "supplier": "Faiveley Transport",
                "eta_initial": "2026-03-15",
                "eta_updated": "2026-03-15",
                "qty_received": 0,
            },
            {
                "itemCode": "TRACTION_MOTOR_TM",
                "initial_status": "MANQUANT",
                "current_status": "EN_ATTENTE",
                "supplier": "Alstom Internal Supply",
                "eta_initial": "2026-03-22",
                "eta_updated": "2026-03-22",
                "qty_received": 0,
            },
        ],
        "updated_eta_end": "2026-03-31",
        "updated_delay_days": 11,
        "resume_priority": 5,
        "resume_priority_reasoning": (
            "3 pièces critiques toujours manquantes. Pas de livraison reçue. "
            "Prioriser d'autres OF moins bloqués."
        ),
        "plan_b_needed": True,
        "rescheduling_proposal": {
            "label": "Lancer le 26/03 matin (toutes pièces attendues)",
            "slot": "SLOT-2026-03-26-AM",
            "launch_date": "2026-03-26",
            "estimated_completion": "2026-03-31",
            "delay_client_days": 11,
            "penalty_eur": 55000,
        },
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
                "predicted_eta": "2026-03-15",
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
                "predicted_eta": "2026-03-26",
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
                "predicted_eta": "2026-03-22",
                "confidence": 0.82,
            },
        ],
    },
}


# =============================================================================
# Sentinelle — run
# =============================================================================

def get_stock_updates_preview(orders: Dict, watchlist: List[Dict]) -> List[Dict]:
    """Aperçu des mises à jour stock simulées pour chaque OF en watchlist."""
    previews = []
    for entry in watchlist:
        of_id = entry["of_id"]
        order = orders[of_id]
        scenario = order["scenario"]
        sim_stock = _SIMULATED_STOCK_SENTINELLE.get(scenario, {})
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


def run_sentinelle(orders: Dict, maestro_outputs: Dict, watchlist: List[Dict]) -> List[Dict]:
    """Sentinelle surveille les hypothèses Maestro et met à jour le risque."""
    results = []
    now = datetime.now(timezone.utc).isoformat()

    for entry in watchlist:
        of_id = entry["of_id"]
        order = orders[of_id]
        scenario = order["scenario"]
        a1 = maestro_outputs.get(of_id, {})
        missing_from_maestro = a1.get("missing_components", [])

        # Stock simulé "actuel"
        simulated_stock = _SIMULATED_STOCK_SENTINELLE.get(scenario, {})
        full_stock = {**order["stock"], **simulated_stock}

        # Tracking arrivées
        stock_arrivals = []
        missing_codes = {mc["itemCode"] for mc in missing_from_maestro}
        for item_code in missing_codes:
            old_qty = order["stock"].get(item_code, 0)
            new_qty = full_stock.get(item_code, 0)
            stock_arrivals.append({
                "itemCode": item_code,
                "stock_maestro": old_qty,
                "stock_sentinelle": new_qty,
                "delta": new_qty - old_qty,
            })

        # Résolutions
        resolved = []
        still_missing = []
        for mc in missing_from_maestro:
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

        ai = _SIMULATED_SENTINELLE.get(scenario, {})

        # Statut : si tout est résolu → risque levé
        if len(still_missing) == 0:
            new_status = "RisqueLeve"
        else:
            new_status = "RisqueConfirme"

        output = {
            "of_id": of_id,
            "previous_status": order["status"],
            "new_status": new_status,
            "timestamp": now,
            # ── Évolution du risque ──
            "initial_risk_level": ai.get("initial_risk_level", a1.get("risk_level", "?")),
            "current_risk_level": ai.get("current_risk_level", "?"),
            "risk_evolution": ai.get("risk_evolution", "STABLE"),
            "warning_status": ai.get("warning_status", "EN_SURVEILLANCE"),
            "sentinelle_message": ai.get("sentinelle_message", ""),
            # ── Suivi pièces ──
            "parts_tracking": ai.get("parts_tracking", []),
            "resolved_components": resolved,
            "still_missing_components": still_missing,
            "stock_arrivals": stock_arrivals,
            # ── Impact mis à jour ──
            "updated_eta_end": ai.get("updated_eta_end"),
            "updated_delay_days": ai.get("updated_delay_days", 0),
            "resume_priority": ai.get("resume_priority"),
            "resume_priority_reasoning": ai.get("resume_priority_reasoning", ""),
            # ── Plan B ──
            "plan_b_needed": ai.get("plan_b_needed", False),
            "rescheduling_proposal": ai.get("rescheduling_proposal"),
            # ── Reco fournisseurs ──
            "supplier_recommendations": ai.get("supplier_recommendations", []),
        }

        # Instruction
        if new_status == "RisqueLeve":
            resume_op = a1.get("cutoff_operation", {})
            parts = ", ".join(f"{r['itemCode']}" for r in resolved)
            output["instruction"] = (
                f"✅ Risque levé — pièces reçues ({parts}). "
                f"Production peut continuer normalement."
            )
        else:
            shortage = ", ".join(f"{sm['itemCode']} (manque {sm['qtyStillShort']})" for sm in still_missing)
            output["instruction"] = f"⏳ Risque confirmé — manquants : {shortage}."

        # Mise à jour statut OF
        order["status"] = new_status
        order["last_agent"] = "Sentinelle"

        results.append(output)

    return results


def resume_of(of_id: str, orders: Dict) -> None:
    """Passe un OF en Released (reprise production — plan B worst case)."""
    order = orders.get(of_id)
    if order:
        order["status"] = "Released"
        order["last_agent"] = "Reprise"


# =============================================================================
# LLM — Prompts et appel
# =============================================================================

MAESTRO_SYSTEM_PROMPT = """Tu es Maestro, expert en planification de production ferroviaire (Alstom).

Tu analyses un Ordre de Fabrication (OF) pour anticiper les risques de blocage en production.
La question clé : "Si je lance maintenant, y a-t-il un risque réaliste que la production
atteigne une étape avant que les pièces nécessaires n'arrivent ?"

Pour chaque OF, tu produis :
1. Un niveau de risque : VERT (aucun risque) / ORANGE (risque mais gérable) / ROUGE (blocage quasi certain)
2. Un score de risque (0-100)
3. Une recommandation : LANCER_IMMEDIAT, LANCER_DECALE (avec date/créneau), ou REPORTER_ET_REPLANIFIER
4. Le temps de traversée jusqu'à l'étape à risque vs l'ETA des pièces
5. Un plan de commande fournisseur si nécessaire
6. Une explication métier détaillée en français

Réponds en JSON valide :
{
  "risk_level": "VERT | ORANGE | ROUGE",
  "global_risk_score": <0-100>,
  "recommended_action": "LANCER_IMMEDIAT | LANCER_DECALE | REPORTER_ET_REPLANIFIER",
  "recommended_launch_date": "<YYYY-MM-DD ou null>",
  "etape_a_risque": {"operationId": "...", "time_to_reach_days": <float>, "composant_manquant": "..."},
  "probabilite_blocage_pct": <0-100>,
  "estimated_delay_days": <number>,
  "maestro_message": "<message clair pour le planificateur>",
  "reasoning": "<explication détaillée>",
  "risk_factors": [{"factor": "...", "score": <0-100>, "detail": "..."}],
  "supplier_order_plan": [{"itemCode": "...", "supplier_name": "...", "order_qty": ..., "estimated_lead_days": ..., "predicted_eta": "..."}]
}"""

SENTINELLE_SYSTEM_PROMPT = """Tu es Sentinelle, agent de surveillance pour l'industrie ferroviaire (Alstom).

Tu surveilles les OF pour lesquels Maestro a identifié un risque. Tu mets à jour en continu :
- Le niveau de risque (VERT / ORANGE / ROUGE)
- L'avancement des livraisons fournisseurs
- L'impact sur la date de fin et le retard client

Ton objectif n'est pas de gérer les blocages, mais de lever les warnings quand les hypothèses
se confirment : "On a reçu les pièces dans les temps, le risque est levé."

En cas critique, tu proposes des créneaux alternatifs de reprogrammation.

Réponds en JSON valide :
{
  "initial_risk_level": "...",
  "current_risk_level": "...",
  "risk_evolution": "BAISSE | STABLE | HAUSSE",
  "warning_status": "LEVE | CONFIRME | EN_SURVEILLANCE",
  "sentinelle_message": "<message clair>",
  "parts_tracking": [{"itemCode": "...", "current_status": "REÇU|EN_ATTENTE", "eta_updated": "..."}],
  "updated_delay_days": <number>,
  "plan_b_needed": <bool>,
  "rescheduling_proposal": {"launch_date": "...", "delay_client_days": ...} | null
}"""


def build_live_context_maestro(
    of_data: Dict, stock: Dict, missing: List,
    cutoff_op, last_doable,
) -> str:
    """Construit le prompt contextuel pour Maestro."""
    components = BOM_FULL
    quantity = of_data["quantity"]
    missing_codes = {mc["itemCode"] for mc in missing}

    lines = [
        "# Analyse de planification OF — Maestro", "",
        "## OF en cours",
        f"- ID : {of_data['of_id']}",
        f"- Produit : {of_data['productCode']}",
        f"- Quantité : {quantity}",
        f"- Priorité : {of_data['priority']}",
        f"- Échéance : {of_data['dueDate']}",
        "", "## BOM — Composants",
    ]
    for comp in components:
        needed = comp["qtyPerUnit"] * quantity
        avail = stock.get(comp["itemCode"], 0)
        crit = "🔴 CRITIQUE" if comp.get("isCritical") else "⚪"
        icon = "✅" if avail >= needed else "❌"
        lines.append(f"- {icon} {comp['itemCode']} ({crit}) — besoin {needed}, dispo {avail}")

    lines += ["", "## Gamme de fabrication avec timing"]
    for op in ROUTING:
        blocked = set(op.get("requiredComponents", [])) & missing_codes
        icon = "🔴 BLOQUÉ" if blocked else "🟢 OK"
        days = round(op["cumulative_start_hours"] / WORK_HOURS_PER_DAY, 1)
        lines.append(
            f"- séq.{op['sequence']} {op['operationId']} — {icon} "
            f"(atteint en {days}j, durée {op['duration_hours']}h)"
        )

    if missing:
        lines += ["", "## Composants manquants et étapes à risque"]
        risk_steps = _find_risk_steps(missing)
        for rs in risk_steps:
            flag = " ⚠️ CRITIQUE" if rs.get("isCritical") else ""
            lines.append(
                f"- {rs['itemCode']}{flag} — bloque {rs['operationId']} "
                f"(atteint en {rs['time_to_reach_days']}j), manque {rs['qtyShortage']}"
            )

    lines += ["", "## Fournisseurs disponibles"]
    for sup in SUPPLIERS_DATA:
        relevant = set(sup.get("components", [])) & missing_codes
        if relevant:
            lines.append(
                f"- {sup['name']} ({sup['supplierId']}) — {', '.join(relevant)} "
                f"— délai {sup['leadTime_days']}j, fiabilité {sup['reliability']*100:.0f}%"
            )

    lines += ["", "## Historique des OF similaires"]
    for rec in HISTORICAL_OFS_DATA:
        late = f"{rec['daysLate']}j retard" if rec["daysLate"] > 0 else "à l'heure"
        blk = f", bloqué à {rec['blockedAtStep']}" if rec["blockedAtStep"] else ""
        lines.append(f"- {rec['of_id']} — qty {rec['quantity']}, {late}{blk}")

    lines += ["", "## Créneaux machine disponibles"]
    for slot in MACHINE_CALENDAR_DATA:
        if slot["status"] == "available":
            lines.append(
                f"- {slot['slotId']} — {slot['date']} {slot['shift']} "
                f"— charge {slot['currentLoad']*100:.0f}%"
            )

    lines += ["", "## Règles SLA"]
    for rule in SLA_RULES_DATA:
        lines.append(
            f"- Client {rule['client']} ({rule['serviceLevelAgreement']}) "
            f"— retard max {rule['maxAcceptableDelay_days']}j, pénalité {rule['penaltyPerDayLate_eur']}€/j"
        )

    return "\n".join(lines)


def build_live_context_sentinelle(
    of_id: str, of_priority: str, of_due_date: str,
    maestro_state: Dict, stock: Dict,
    still_missing: List, resolved: List,
) -> str:
    """Construit le prompt contextuel pour Sentinelle."""
    lines = [
        "# Surveillance OF — Sentinelle", "",
        "## OF concerné",
        f"- ID : {of_id}",
        f"- Priorité : {of_priority}",
        f"- Échéance : {of_due_date}",
        f"- Risque Maestro : {maestro_state.get('risk_level', '?')} (score {maestro_state.get('global_risk_score', '?')}/100)",
    ]
    etape = maestro_state.get("etape_a_risque")
    if etape:
        lines.append(f"- Étape à risque : {etape.get('operationId', '?')} (atteint en {etape.get('time_to_reach_days', '?')}j)")

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
        lines += ["", "## Fournisseurs"]
        for sup in SUPPLIERS_DATA:
            relevant = set(sup.get("components", [])) & missing_codes
            if relevant:
                lines.append(f"- {sup['name']} — {', '.join(relevant)} — délai {sup['leadTime_days']}j")

    lines += ["", "## SLA"]
    for rule in SLA_RULES_DATA:
        lines.append(f"- {rule['client']} — retard max {rule['maxAcceptableDelay_days']}j, pénalité {rule['penaltyPerDayLate_eur']}€/j")

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
