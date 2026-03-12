# """Seed data et logique simulée — Maestro & Sentinelle.

# Cadrage : Anticiper les risques de blocage et de retard AVANT qu'ils n'arrivent.
# Maestro regarde en avance le film de production.
# Sentinelle surveille les hypothèses prises par Maestro.

# Contient :
#   - Les 3 scénarios (OK / Moyen / Critique) avec cadrage anticipation des retards
#   - run_maestro, run_sentinelle, run_orchestrator
#   - Données de référence (BOM, routing avec timing, fournisseurs, etc.)
# """

# from datetime import datetime, timezone, timedelta
# from typing import Any, Dict, List, Optional
# import copy
# import json
# import os


# # =============================================================================
# # Gamme de fabrication avec timing (heures)
# # =============================================================================

# ROUTING = [
#     {
#         "operationId": "OP10_FRAME_PREP",
#         "sequence": 10,
#         "description": "Préparation châssis",
#         "requiredComponents": ["BOGIE_FRAME_Y32"],
#         "duration_hours": 4,
#         "cumulative_start_hours": 0,
#         "cumulative_end_hours": 4,
#     },
#     {
#         "operationId": "OP20_WHEELSET_MOUNT",
#         "sequence": 20,
#         "description": "Montage essieux + boîtes",
#         "requiredComponents": ["WHEELSET_920MM", "AXLE_BOX"],
#         "duration_hours": 8,
#         "cumulative_start_hours": 4,
#         "cumulative_end_hours": 12,
#     },
#     {
#         "operationId": "OP30_SUSPENSION",
#         "sequence": 30,
#         "description": "Installation suspension",
#         "requiredComponents": ["SUSPENSION_SPRING"],
#         "duration_hours": 6,
#         "cumulative_start_hours": 12,
#         "cumulative_end_hours": 18,
#     },
#     {
#         "operationId": "OP40_BRAKE_ASSEMBLY",
#         "sequence": 40,
#         "description": "Montage freins",
#         "requiredComponents": ["BRAKE_DISC"],
#         "duration_hours": 8,
#         "cumulative_start_hours": 18,
#         "cumulative_end_hours": 26,
#     },
#     {
#         "operationId": "OP50_TRACTION_MOTOR",
#         "sequence": 50,
#         "description": "Installation moteur traction",
#         "requiredComponents": ["TRACTION_MOTOR_TM"],
#         "duration_hours": 8,
#         "cumulative_start_hours": 26,
#         "cumulative_end_hours": 34,
#     },
#     {
#         "operationId": "OP60_TESTING",
#         "sequence": 60,
#         "description": "Tests et contrôle qualité",
#         "requiredComponents": [],
#         "duration_hours": 6,
#         "cumulative_start_hours": 34,
#         "cumulative_end_hours": 40,
#     },
# ]

# WORK_HOURS_PER_DAY = 8  # 8h utiles par jour ouvré


# # =============================================================================
# # BOM — Nomenclature
# # =============================================================================

# BOM_FULL = [
#     {"itemCode": "BOGIE_FRAME_Y32",  "description": "Châssis bogie Y32 soudé",       "qtyPerUnit": 1, "isCritical": True},
#     {"itemCode": "WHEELSET_920MM",    "description": "Essieu monté roue Ø920mm",      "qtyPerUnit": 2, "isCritical": True},
#     {"itemCode": "AXLE_BOX",          "description": "Boîte d'essieu",                "qtyPerUnit": 4, "isCritical": False},
#     {"itemCode": "SUSPENSION_SPRING", "description": "Ressort de suspension primaire", "qtyPerUnit": 4, "isCritical": False},
#     {"itemCode": "BRAKE_DISC",        "description": "Disque de frein",                "qtyPerUnit": 4, "isCritical": True},
#     {"itemCode": "TRACTION_MOTOR_TM", "description": "Moteur de traction",            "qtyPerUnit": 2, "isCritical": True},
# ]

# DEFAULT_STOCK = {
#     "BOGIE_FRAME_Y32": 6,
#     "WHEELSET_920MM": 10,
#     "AXLE_BOX": 20,
#     "SUSPENSION_SPRING": 18,
#     "BRAKE_DISC": 0,
#     "TRACTION_MOTOR_TM": 9,
# }


# # =============================================================================
# # Fournisseurs
# # =============================================================================

# SUPPLIERS_DATA = [
#     {"supplierId": "SUP-KNORR",      "name": "Knorr-Bremse",          "email": "commercial@knorr-bremse.com",  "components": ["BRAKE_DISC"],        "leadTime_days": 5,  "reliability": 0.85, "unitPrice_eur": 320,   "minOrderQty": 8},
#     {"supplierId": "SUP-FAIVELEY",   "name": "Faiveley Transport",    "email": "commandes@faiveley.com",       "components": ["BRAKE_DISC"],        "leadTime_days": 3,  "reliability": 0.95, "unitPrice_eur": 380,   "minOrderQty": 4},
#     {"supplierId": "SUP-ALSTOM-INT", "name": "Alstom Internal Supply", "email": "supply.internal@alstom.com",  "components": ["TRACTION_MOTOR_TM"], "leadTime_days": 10, "reliability": 0.90, "unitPrice_eur": 12000, "minOrderQty": 1},
#     {"supplierId": "SUP-GHH",        "name": "GHH-Bonatrans",         "email": "orders@ghh-bonatrans.com",     "components": ["WHEELSET_920MM"],    "leadTime_days": 14, "reliability": 0.92, "unitPrice_eur": 8500,  "minOrderQty": 2},
# ]

# HISTORICAL_OFS_DATA = [
#     {"of_id": "of-2025-00087", "quantity": 2, "daysLate": 3, "wasPartialRelease": True,  "blockedComponents": ["BRAKE_DISC"],                        "blockedAtStep": "OP40"},
#     {"of_id": "of-2025-00112", "quantity": 4, "daysLate": 0, "wasPartialRelease": False, "blockedComponents": [],                                     "blockedAtStep": None},
#     {"of_id": "of-2025-00148", "quantity": 6, "daysLate": 4, "wasPartialRelease": True,  "blockedComponents": ["BRAKE_DISC", "TRACTION_MOTOR_TM"],   "blockedAtStep": "OP40"},
#     {"of_id": "of-2026-00015", "quantity": 3, "daysLate": 0, "wasPartialRelease": False, "blockedComponents": [],                                     "blockedAtStep": None},
#     {"of_id": "of-2026-00058", "quantity": 4, "daysLate": 3, "wasPartialRelease": True,  "blockedComponents": ["BRAKE_DISC"],                        "blockedAtStep": "OP40"},
# ]

# MACHINE_CALENDAR_DATA = [
#     {"slotId": "SLOT-2026-03-12-AM", "date": "2026-03-12", "shift": "Matin (06h–14h)",       "availableHours": 8, "currentLoad": 0.30, "status": "available"},
#     {"slotId": "SLOT-2026-03-12-PM", "date": "2026-03-12", "shift": "Après-midi (14h–22h)", "availableHours": 0, "currentLoad": 1.00, "status": "maintenance"},
#     {"slotId": "SLOT-2026-03-13-AM", "date": "2026-03-13", "shift": "Matin (06h–14h)",       "availableHours": 8, "currentLoad": 0.20, "status": "available"},
#     {"slotId": "SLOT-2026-03-13-PM", "date": "2026-03-13", "shift": "Après-midi (14h–22h)", "availableHours": 8, "currentLoad": 0.40, "status": "available"},
#     {"slotId": "SLOT-2026-03-14-AM", "date": "2026-03-14", "shift": "Matin (06h–14h)",       "availableHours": 8, "currentLoad": 0.50, "status": "available"},
#     {"slotId": "SLOT-2026-03-14-PM", "date": "2026-03-14", "shift": "Après-midi (14h–22h)", "availableHours": 8, "currentLoad": 0.35, "status": "available"},
#     {"slotId": "SLOT-2026-03-17-AM", "date": "2026-03-17", "shift": "Matin (06h–14h)",       "availableHours": 8, "currentLoad": 0.60, "status": "available"},
#     {"slotId": "SLOT-2026-03-26-AM", "date": "2026-03-26", "shift": "Matin (06h–14h)",       "availableHours": 8, "currentLoad": 0.10, "status": "available"},
# ]

# SLA_RULES_DATA = [
#     {"client": "SNCF_TGV", "serviceLevelAgreement": "Premium", "maxAcceptableDelay_days": 2, "penaltyPerDayLate_eur": 5000},
#     {"client": "DEFAULT",  "serviceLevelAgreement": "Standard", "maxAcceptableDelay_days": 5, "penaltyPerDayLate_eur": 1500},
# ]


# # =============================================================================
# # Seed data — 3 scénarios
# # =============================================================================

# def build_seed_orders() -> Dict[str, Dict]:
#     """Retourne les 3 OF de démonstration indexés par of_id."""
#     return {
#         # ── Scénario OK ──────────────────────────────────────────
#         "of-2026-00200": {
#             "of_id": "of-2026-00200",
#             "scenario": "OK",
#             "scenario_label": "✅ Scénario OK — Stock suffisant, aucun risque",
#             "orderNumber": "OF-2026-00200",
#             "productCode": "BOGIE_Y32",
#             "quantity": 2,
#             "priority": "Medium",
#             "status": "Created",
#             "dueDate": "2026-04-10T00:00:00Z",
#             "components": [
#                 {"itemCode": "BOGIE_FRAME_Y32", "qtyPerUnit": 1, "isCritical": True},
#                 {"itemCode": "WHEELSET_920MM",  "qtyPerUnit": 2, "isCritical": True},
#                 {"itemCode": "AXLE_BOX",        "qtyPerUnit": 4, "isCritical": False},
#                 {"itemCode": "SUSPENSION_SPRING","qtyPerUnit": 4, "isCritical": False},
#                 {"itemCode": "BRAKE_DISC",      "qtyPerUnit": 4, "isCritical": True},
#                 {"itemCode": "TRACTION_MOTOR_TM","qtyPerUnit": 2, "isCritical": True},
#             ],
#             "stock": {
#                 "BOGIE_FRAME_Y32": 5,
#                 "WHEELSET_920MM": 10,
#                 "AXLE_BOX": 20,
#                 "SUSPENSION_SPRING": 18,
#                 "BRAKE_DISC": 20,
#                 "TRACTION_MOTOR_TM": 9,
#             },
#             "historical_risk": "LOW",
#         },
#         # ── Scénario Moyen ──────────────────────────────────────
#         "of-2026-00201": {
#             "of_id": "of-2026-00201",
#             "scenario": "Moyen",
#             "scenario_label": "⚠️ Scénario Moyen — Pièce manquante, ETA serrée",
#             "orderNumber": "OF-2026-00201",
#             "productCode": "BOGIE_Y32",
#             "quantity": 4,
#             "priority": "High",
#             "status": "Created",
#             "dueDate": "2026-03-25T00:00:00Z",
#             "components": [
#                 {"itemCode": "BOGIE_FRAME_Y32", "qtyPerUnit": 1, "isCritical": True},
#                 {"itemCode": "WHEELSET_920MM",  "qtyPerUnit": 2, "isCritical": True},
#                 {"itemCode": "AXLE_BOX",        "qtyPerUnit": 4, "isCritical": False},
#                 {"itemCode": "SUSPENSION_SPRING","qtyPerUnit": 4, "isCritical": False},
#                 {"itemCode": "BRAKE_DISC",      "qtyPerUnit": 4, "isCritical": True},
#                 {"itemCode": "TRACTION_MOTOR_TM","qtyPerUnit": 2, "isCritical": True},
#             ],
#             "stock": {
#                 "BOGIE_FRAME_Y32": 6,
#                 "WHEELSET_920MM": 10,
#                 "AXLE_BOX": 20,
#                 "SUSPENSION_SPRING": 18,
#                 "BRAKE_DISC": 0,       # ← manquant
#                 "TRACTION_MOTOR_TM": 9,
#             },
#             "historical_risk": "MEDIUM",
#         },
#         # ── Scénario Critique ───────────────────────────────────
#         "of-2026-00202": {
#             "of_id": "of-2026-00202",
#             "scenario": "Critique",
#             "scenario_label": "🛑 Scénario Critique — Risque majeur de blocage",
#             "orderNumber": "OF-2026-00202",
#             "productCode": "BOGIE_Y32",
#             "quantity": 6,
#             "priority": "High",
#             "status": "Created",
#             "dueDate": "2026-03-20T00:00:00Z",
#             "components": [
#                 {"itemCode": "BOGIE_FRAME_Y32", "qtyPerUnit": 1, "isCritical": True},
#                 {"itemCode": "WHEELSET_920MM",  "qtyPerUnit": 2, "isCritical": True},
#                 {"itemCode": "AXLE_BOX",        "qtyPerUnit": 4, "isCritical": False},
#                 {"itemCode": "SUSPENSION_SPRING","qtyPerUnit": 4, "isCritical": False},
#                 {"itemCode": "BRAKE_DISC",      "qtyPerUnit": 4, "isCritical": True},
#                 {"itemCode": "TRACTION_MOTOR_TM","qtyPerUnit": 2, "isCritical": True},
#             ],
#             "stock": {
#                 "BOGIE_FRAME_Y32": 6,
#                 "WHEELSET_920MM": 4,   # ← manquant (besoin 12)
#                 "AXLE_BOX": 24,
#                 "SUSPENSION_SPRING": 24,
#                 "BRAKE_DISC": 0,       # ← manquant (besoin 24)
#                 "TRACTION_MOTOR_TM": 2, # ← manquant (besoin 12)
#             },
#             "historical_risk": "HIGH",
#         },
#     }


# # =============================================================================
# # Helpers — analyse de production
# # =============================================================================

# def _check_availability(components, quantity, stock):
#     """Calcule les composants manquants."""
#     missing = []
#     for comp in components:
#         needed = comp["qtyPerUnit"] * quantity
#         available = stock.get(comp["itemCode"], 0)
#         if available < needed:
#             missing.append({
#                 "itemCode": comp["itemCode"],
#                 "qtyNeeded": needed,
#                 "qtyAvailable": available,
#                 "qtyShortage": needed - available,
#                 "isCritical": comp.get("isCritical", False),
#             })
#     return missing


# def _find_cutoff(operations, missing_components):
#     """Trouve la 1ère opération bloquée par un composant manquant."""
#     missing_codes = {mc["itemCode"] for mc in missing_components}
#     for op in operations:
#         if set(op.get("requiredComponents", [])) & missing_codes:
#             return op
#     return None


# def _find_last_doable(operations, cutoff_op):
#     """Dernière opération faisable avant la coupure."""
#     if cutoff_op is None:
#         return None
#     cutoff_seq = cutoff_op["sequence"]
#     doable = [op for op in operations if op["sequence"] < cutoff_seq]
#     return doable[-1] if doable else None


# def _find_risk_steps(missing_components):
#     """Pour chaque composant manquant, trouve l'étape qui le consomme et le temps pour y arriver."""
#     risk_steps = []
#     missing_codes = {mc["itemCode"] for mc in missing_components}
#     for op in ROUTING:
#         blocked_items = set(op.get("requiredComponents", [])) & missing_codes
#         if blocked_items:
#             for item in blocked_items:
#                 mc = next(m for m in missing_components if m["itemCode"] == item)
#                 risk_steps.append({
#                     "itemCode": item,
#                     "operationId": op["operationId"],
#                     "sequence": op["sequence"],
#                     "description": op["description"],
#                     "time_to_reach_hours": op["cumulative_start_hours"],
#                     "time_to_reach_days": round(op["cumulative_start_hours"] / WORK_HOURS_PER_DAY, 1),
#                     "qtyShortage": mc["qtyShortage"],
#                     "isCritical": mc.get("isCritical", False),
#                 })
#     return risk_steps


# def _build_simulated_email(supplier, item_code, qty, of_number, risk_step_op, delivery_date):
#     """Construit un email fournisseur simulé."""
#     return {
#         "to": f"{supplier['email']}",
#         "to_name": supplier["name"],
#         "supplier_id": supplier["supplierId"],
#         "subject": f"[URGENT] Commande {item_code} × {qty} — {of_number}",
#         "body": (
#             f"Bonjour,\n\n"
#             f"Dans le cadre de l'{of_number}, nous avons un besoin urgent de "
#             f"{qty} unité(s) de {item_code}.\n\n"
#             f"Stock actuel : 0 / Besoin : {qty}\n"
#             f"Date de livraison souhaitée : {delivery_date}\n"
#             f"Impact si retard : blocage à l'étape {risk_step_op}\n\n"
#             f"Merci de confirmer disponibilité et délai de livraison.\n\n"
#             f"Cordialement,\n"
#             f"Système Maestro — Planification IA Alstom"
#         ),
#     }


# # =============================================================================
# # Maestro — Outputs simulés par scénario
# # =============================================================================

# _SIMULATED_MAESTRO = {
#     "OK": {
#         "risk_level": "VERT",
#         "global_risk_score": 8,
#         "recommended_action": "LANCER_IMMEDIAT",
#         "recommended_launch_date": "2026-03-12",
#         "recommended_launch_slot": "SLOT-2026-03-12-AM",
#         "estimated_production_days": 5,
#         # ── Risque retard ──
#         "probabilite_blocage_pct": 0,
#         "estimated_delay_days": 0,
#         "estimated_penalty_eur": 0,
#         "etape_a_risque": None,
#         # ── Messages ──
#         "maestro_message": (
#             "Tous les composants sont disponibles en quantité suffisante pour l'ensemble de la gamme. "
#             "Aucun risque de blocage à aucune étape. Pas de retard attendu, on lance comme prévu."
#         ),
#         "reasoning": (
#             "Stock complet vérifié sur les 6 composants. Marge confortable de ~27 jours avant "
#             "échéance. L'historique ne montre aucun blocage récent sur ce type d'OF. "
#             "Le créneau du 12/03 matin est disponible (charge 30 %). "
#             "Recommandation : lancer la production immédiatement."
#         ),
#         "risk_factors": [
#             {"factor": "Stock",      "score": 5,  "detail": "Tous composants disponibles"},
#             {"factor": "Historique", "score": 10, "detail": "Aucun retard récent"},
#             {"factor": "Échéance",   "score": 5,  "detail": "27 jours de marge"},
#             {"factor": "Planning",   "score": 15, "detail": "Créneaux dégagés"},
#         ],
#         "supplier_order_plan": [],
#         "simulated_emails": [],
#         "rescheduling_options": [],
#         "sla_impact": "Aucun risque SLA — livraison bien avant l'échéance.",
#     },
#     "Moyen": {
#         "risk_level": "ORANGE",
#         "global_risk_score": 55,
#         "recommended_action": "LANCER_DECALE",
#         "recommended_launch_date": "2026-03-13",
#         "recommended_launch_slot": "SLOT-2026-03-13-AM",
#         "estimated_production_days": 5,
#         # ── Risque retard ──
#         "probabilite_blocage_pct": 30,
#         "estimated_delay_days": 0,
#         "estimated_penalty_eur": 0,
#         "etape_a_risque": {
#             "operationId": "OP40_BRAKE_ASSEMBLY",
#             "sequence": 40,
#             "description": "Montage freins",
#             "time_to_reach_days": 2.25,
#             "composant_manquant": "BRAKE_DISC",
#         },
#         # ── Messages ──
#         "maestro_message": (
#             "Le composant BRAKE_DISC est absent du stock. Il est consommé à l'étape OP40 "
#             "(Montage freins), que la production atteindra au bout de ~2,25 jours. "
#             "Le fournisseur Faiveley Transport peut livrer sous 3 jours. "
#             "Si on lance demain matin (13/03), la production atteindra OP40 le 15/03 après-midi, "
#             "et les freins seront livrés le 15/03 au plus tard. C'est serré mais réaliste. "
#             "Garde un œil sur la confirmation fournisseur."
#         ),
#         "reasoning": (
#             "BRAKE_DISC manquant (besoin 16, stock 0). Consommé à OP40 (séq. 40), "
#             "étape atteinte en 18h de production soit ~2,25 jours ouvrés. "
#             "Meilleur fournisseur : Faiveley Transport (fiabilité 95 %, délai 3 j). "
#             "Si lancement immédiat → arrive à OP40 le 14/03 après-midi, freins livrés le 15/03 → "
#             "0,5 j d'attente potentielle. Si lancement décalé au 13/03 matin → arrive à OP40 le "
#             "15/03 après-midi, freins livrés le 15/03 → timing aligné. "
#             "Historique : 3-4 j de retard sur OF similaires bloqués par BRAKE_DISC."
#         ),
#         "risk_factors": [
#             {"factor": "Composant critique manquant", "score": 75, "detail": "BRAKE_DISC absent, consommé à OP40"},
#             {"factor": "Timing pièce vs étape",       "score": 50, "detail": "ETA fournisseur (3j) ≈ temps d'arrivée à OP40 (2,25j)"},
#             {"factor": "Historique retards",            "score": 55, "detail": "3-4 j retard historique sur BRAKE_DISC"},
#             {"factor": "Échéance / SLA",                "score": 40, "detail": "13 j restants, pénalité 5 000 €/j au-delà de +2 j"},
#         ],
#         "supplier_order_plan": [
#             {
#                 "itemCode": "BRAKE_DISC",
#                 "recommended_supplier": "SUP-FAIVELEY",
#                 "supplier_name": "Faiveley Transport",
#                 "order_qty": 16,
#                 "unit_price_eur": 380,
#                 "total_price_eur": 6080,
#                 "estimated_lead_days": 3,
#                 "order_date": "2026-03-12",
#                 "predicted_eta": "2026-03-15",
#                 "confidence": 0.92,
#             },
#         ],
#         "simulated_emails": [
#             {
#                 "to": "commandes@faiveley.com",
#                 "to_name": "Faiveley Transport",
#                 "supplier_id": "SUP-FAIVELEY",
#                 "subject": "[URGENT] Commande BRAKE_DISC × 16 — OF-2026-00201",
#                 "body": (
#                     "Bonjour,\n\n"
#                     "Dans le cadre de l'OF-2026-00201 (4 bogies Y32), nous avons un besoin "
#                     "urgent de 16 disques de frein (BRAKE_DISC).\n\n"
#                     "Stock actuel : 0 / Besoin : 16\n"
#                     "Date de livraison souhaitée : 15/03/2026\n"
#                     "Impact si retard : blocage à l'étape OP40 (Montage freins)\n\n"
#                     "Merci de confirmer disponibilité et délai de livraison.\n\n"
#                     "Cordialement,\n"
#                     "Système Maestro — Planification IA Alstom"
#                 ),
#             },
#         ],
#         "rescheduling_options": [],
#         "sla_impact": (
#             "Si les BRAKE_DISC arrivent sous 3 jours, l'OF reste dans le SLA. "
#             "Au-delà, pénalité de 5 000 €/jour."
#         ),
#     },
#     "Critique": {
#         "risk_level": "ROUGE",
#         "global_risk_score": 92,
#         "recommended_action": "REPORTER_ET_REPLANIFIER",
#         "recommended_launch_date": None,
#         "recommended_launch_slot": None,
#         "estimated_production_days": 5,
#         # ── Risque retard ──
#         "probabilite_blocage_pct": 95,
#         "estimated_delay_days": 10,
#         "estimated_penalty_eur": 50000,
#         "etape_a_risque": {
#             "operationId": "OP20_WHEELSET_MOUNT",
#             "sequence": 20,
#             "description": "Montage essieux + boîtes",
#             "time_to_reach_days": 0.5,
#             "composant_manquant": "WHEELSET_920MM",
#         },
#         # ── Messages ──
#         "maestro_message": (
#             "3 composants critiques manquants : WHEELSET_920MM, BRAKE_DISC, TRACTION_MOTOR_TM. "
#             "Le premier blocage (WHEELSET) apparaît à OP20, atteint en seulement 4h (0,5 jour). "
#             "Le fournisseur le plus rapide pour les WHEELSET (GHH-Bonatrans) a un délai de 14 jours. "
#             "Dans toutes les hypothèses réalistes, la production sera bloquée quasi immédiatement. "
#             "Ne pas lancer maintenant. Deux créneaux de reprogrammation sont proposés."
#         ),
#         "reasoning": (
#             "3 composants critiques absents :\n"
#             "• WHEELSET_920MM — besoin 12, dispo 4, manque 8 → bloque OP20 (atteint en 0,5 j)\n"
#             "• BRAKE_DISC — besoin 24, dispo 0, manque 24 → bloque OP40 (atteint en 2,25 j)\n"
#             "• TRACTION_MOTOR_TM — besoin 12, dispo 2, manque 10 → bloque OP50 (atteint en 3,25 j)\n"
#             "Réappro le plus lent : WHEELSET_920MM (14 j via GHH-Bonatrans). "
#             "Échéance dans 8 jours : retard quasi certain de 8-10 jours. "
#             "Pénalités estimées : 5 000 €/j × 10 j = 50 000 €."
#         ),
#         "risk_factors": [
#             {"factor": "Composants critiques manquants",  "score": 95, "detail": "3 pièces critiques absentes"},
#             {"factor": "Timing pièce vs étape",           "score": 98, "detail": "OP20 atteint en 0,5 j, pièces livrées en 14 j"},
#             {"factor": "Historique retards",               "score": 85, "detail": "7 j attente stock historique"},
#             {"factor": "Échéance / SLA",                   "score": 95, "detail": "8 j restants, réappro 14 j — retard certain"},
#         ],
#         "supplier_order_plan": [
#             {
#                 "itemCode": "BRAKE_DISC",
#                 "recommended_supplier": "SUP-FAIVELEY",
#                 "supplier_name": "Faiveley Transport",
#                 "order_qty": 24,
#                 "unit_price_eur": 380,
#                 "total_price_eur": 9120,
#                 "estimated_lead_days": 3,
#                 "order_date": "2026-03-12",
#                 "predicted_eta": "2026-03-15",
#                 "confidence": 0.92,
#             },
#             {
#                 "itemCode": "WHEELSET_920MM",
#                 "recommended_supplier": "SUP-GHH",
#                 "supplier_name": "GHH-Bonatrans",
#                 "order_qty": 8,
#                 "unit_price_eur": 8500,
#                 "total_price_eur": 68000,
#                 "estimated_lead_days": 14,
#                 "order_date": "2026-03-12",
#                 "predicted_eta": "2026-03-26",
#                 "confidence": 0.78,
#             },
#             {
#                 "itemCode": "TRACTION_MOTOR_TM",
#                 "recommended_supplier": "SUP-ALSTOM-INT",
#                 "supplier_name": "Alstom Internal Supply",
#                 "order_qty": 10,
#                 "unit_price_eur": 12000,
#                 "total_price_eur": 120000,
#                 "estimated_lead_days": 10,
#                 "order_date": "2026-03-12",
#                 "predicted_eta": "2026-03-22",
#                 "confidence": 0.82,
#             },
#         ],
#         "simulated_emails": [
#             {
#                 "to": "orders@ghh-bonatrans.com",
#                 "to_name": "GHH-Bonatrans",
#                 "supplier_id": "SUP-GHH",
#                 "subject": "[URGENT] Commande WHEELSET_920MM × 8 — OF-2026-00202",
#                 "body": (
#                     "Bonjour,\n\n"
#                     "Dans le cadre de l'OF-2026-00202 (6 bogies Y32), nous avons un besoin "
#                     "urgent de 8 essieux montés (WHEELSET_920MM).\n\n"
#                     "Stock actuel : 4 / Besoin : 12\n"
#                     "Date de livraison souhaitée : 26/03/2026\n"
#                     "Impact si retard : blocage à l'étape OP20 (Montage essieux)\n\n"
#                     "Merci de confirmer disponibilité et délai de livraison.\n\n"
#                     "Cordialement,\n"
#                     "Système Maestro — Planification IA Alstom"
#                 ),
#             },
#             {
#                 "to": "commandes@faiveley.com",
#                 "to_name": "Faiveley Transport",
#                 "supplier_id": "SUP-FAIVELEY",
#                 "subject": "[URGENT] Commande BRAKE_DISC × 24 — OF-2026-00202",
#                 "body": (
#                     "Bonjour,\n\n"
#                     "Dans le cadre de l'OF-2026-00202 (6 bogies Y32), nous avons un besoin "
#                     "urgent de 24 disques de frein (BRAKE_DISC).\n\n"
#                     "Stock actuel : 0 / Besoin : 24\n"
#                     "Date de livraison souhaitée : 15/03/2026\n"
#                     "Impact si retard : blocage à l'étape OP40 (Montage freins)\n\n"
#                     "Merci de confirmer disponibilité et délai de livraison.\n\n"
#                     "Cordialement,\n"
#                     "Système Maestro — Planification IA Alstom"
#                 ),
#             },
#             {
#                 "to": "supply.internal@alstom.com",
#                 "to_name": "Alstom Internal Supply",
#                 "supplier_id": "SUP-ALSTOM-INT",
#                 "subject": "[URGENT] Commande TRACTION_MOTOR_TM × 10 — OF-2026-00202",
#                 "body": (
#                     "Bonjour,\n\n"
#                     "Dans le cadre de l'OF-2026-00202 (6 bogies Y32), nous avons un besoin "
#                     "urgent de 10 moteurs de traction (TRACTION_MOTOR_TM).\n\n"
#                     "Stock actuel : 2 / Besoin : 12\n"
#                     "Date de livraison souhaitée : 22/03/2026\n"
#                     "Impact si retard : blocage à l'étape OP50 (Moteur traction)\n\n"
#                     "Merci de confirmer disponibilité et délai de livraison.\n\n"
#                     "Cordialement,\n"
#                     "Système Maestro — Planification IA Alstom"
#                 ),
#             },
#         ],
#         "rescheduling_options": [
#             {
#                 "label": "Créneau A — Lancer le 26/03 matin",
#                 "slot": "SLOT-2026-03-26-AM",
#                 "launch_date": "2026-03-26",
#                 "estimated_completion": "2026-03-31",
#                 "delay_client_days": 11,
#                 "penalty_eur": 55000,
#                 "comment": "Toutes les pièces disponibles. Retard de 11 jours.",
#             },
#             {
#                 "label": "Créneau B — Lancer le 22/03 (risque partiel)",
#                 "slot": "SLOT-2026-03-22-AM",
#                 "launch_date": "2026-03-22",
#                 "estimated_completion": "2026-03-28",
#                 "delay_client_days": 8,
#                 "penalty_eur": 40000,
#                 "comment": (
#                     "BRAKE_DISC et MOTOR disponibles, WHEELSET attendu le 26/03. "
#                     "Risque de blocage à OP20 le 22/03 si WHEELSET en retard."
#                 ),
#             },
#         ],
#         "sla_impact": (
#             "SLA compromis — échéance 20/03, réappro complet estimé à 14 jours. "
#             "Pénalités : 5 000 €/jour × 10+ jours = 50 000 €+."
#         ),
#     },
# }


# # =============================================================================
# # Maestro — run
# # =============================================================================

# def run_maestro(of_id: str, orders: Dict) -> Dict:
#     """Maestro analyse l'OF et produit une recommandation de lancement."""
#     order = orders[of_id]
#     scenario = order["scenario"]
#     components = order["components"]
#     quantity = order["quantity"]
#     stock = order["stock"]

#     # --- Analyse déterministe ---
#     missing = _check_availability(components, quantity, stock)
#     cutoff_op = _find_cutoff(ROUTING, missing)
#     last_doable = _find_last_doable(ROUTING, cutoff_op)
#     risk_steps = _find_risk_steps(missing)

#     # --- IA simulée ---
#     ai = _SIMULATED_MAESTRO[scenario]

#     # Jours avant échéance
#     due_date = datetime.fromisoformat(order["dueDate"].replace("Z", "+00:00"))
#     now_dt = datetime.now(timezone.utc)
#     days_until_due = (due_date - now_dt).days

#     now = now_dt.isoformat()
#     output = {
#         "of_id": of_id,
#         "orderNumber": order["orderNumber"],
#         "productCode": order["productCode"],
#         "quantity": quantity,
#         "timestamp": now,
#         # ── Risque ──
#         "risk_level": ai["risk_level"],
#         "global_risk_score": ai["global_risk_score"],
#         "probabilite_blocage_pct": ai["probabilite_blocage_pct"],
#         "etape_a_risque": ai["etape_a_risque"],
#         "risk_steps": risk_steps,
#         # ── Lancement ──
#         "recommended_action": ai["recommended_action"],
#         "recommended_launch_date": ai["recommended_launch_date"],
#         "recommended_launch_slot": ai["recommended_launch_slot"],
#         "estimated_production_days": ai["estimated_production_days"],
#         # ── Retard ──
#         "days_until_due": days_until_due,
#         "estimated_delay_days": ai["estimated_delay_days"],
#         "estimated_penalty_eur": ai["estimated_penalty_eur"],
#         # ── Messages ──
#         "maestro_message": ai["maestro_message"],
#         "reasoning": ai["reasoning"],
#         "risk_factors": ai["risk_factors"],
#         "sla_impact": ai["sla_impact"],
#         # ── Plan fournisseur ──
#         "supplier_order_plan": ai["supplier_order_plan"],
#         "simulated_emails": ai["simulated_emails"],
#         # ── Reprogrammation (si critique) ──
#         "rescheduling_options": ai["rescheduling_options"],
#         # ── Composants ──
#         "missing_components": missing,
#         "cutoff_operation": {
#             "operationId": cutoff_op["operationId"],
#             "sequence": cutoff_op["sequence"],
#             "description": cutoff_op["description"],
#         } if cutoff_op else None,
#         # ── Statut interne ──
#         "operator_decision": None,
#         "previous_status": order["status"],
#     }

#     # Status intermédiaire : en attente de décision
#     output["new_status"] = "AwaitingDecision"
#     order["status"] = "AwaitingDecision"
#     order["last_agent"] = "Maestro"

#     return output


# # =============================================================================
# # Décision opérateur
# # =============================================================================

# def apply_operator_decision(of_id: str, orders: Dict, maestro_outputs: Dict,
#                             decision: str) -> str:
#     """Applique la décision de l'opérateur sur un OF analysé par Maestro."""
#     order = orders[of_id]
#     output = maestro_outputs[of_id]
#     output["operator_decision"] = decision

#     status_map = {
#         "LANCER_IMMEDIAT": "Released",
#         "LANCER_DECALE": "EnSurveillance",
#         "REPORTER_ET_REPLANIFIER": "Replanifie",
#     }
#     new_status = status_map.get(decision, "AwaitingDecision")
#     output["new_status"] = new_status
#     order["status"] = new_status
#     order["last_agent"] = "Opérateur"

#     missing = output.get("missing_components", [])

#     if decision == "LANCER_IMMEDIAT":
#         if not missing:
#             instruction = "Production complète — tous les composants sont disponibles. Lancer immédiatement."
#         else:
#             shortage = ", ".join(f"{mc['itemCode']} (manque {mc['qtyShortage']})" for mc in missing)
#             instruction = (
#                 f"⚠️ Lancement immédiat sur décision opérateur malgré composants manquants : {shortage}. "
#                 f"Risque de blocage en production."
#             )
#     elif decision == "LANCER_DECALE":
#         slot = output.get("recommended_launch_slot", "?")
#         date_str = output.get("recommended_launch_date", "?")
#         shortage = ", ".join(mc["itemCode"] for mc in missing) if missing else "—"
#         instruction = (
#             f"Lancement prévu le {date_str} (créneau {slot}). "
#             f"Surveiller l'arrivée de : {shortage}. "
#             f"Sentinelle activée pour suivi en continu."
#         )
#     else:  # REPORTER_ET_REPLANIFIER
#         options = output.get("rescheduling_options", [])
#         if options:
#             opt = options[0]
#             instruction = (
#                 f"OF reporté. Créneau de reprogrammation proposé : {opt['label']}. "
#                 f"Retard client estimé : +{opt['delay_client_days']} jours. "
#                 f"Sentinelle activée pour suivi fournisseurs."
#             )
#         else:
#             critical = [mc["itemCode"] for mc in missing if mc.get("isCritical")]
#             instruction = (
#                 f"OF reporté — composants critiques manquants : {', '.join(critical) if critical else 'N/A'}. "
#                 f"En attente de reprogrammation."
#             )

#     output["instruction"] = instruction
#     return instruction

"""
Seed data and simulated logic — Maestro & Sentinelle.


Framing: Anticipate blocking and delay risks BEFORE they happen.
Maestro looks ahead at the production flow.
Sentinelle monitors the assumptions made by Maestro.


Contains:
  - The 3 scenarios (OK / Medium / Critical) with a delay anticipation framing
  - run_maestro, run_sentinelle, run_orchestrator
  - Reference data (BOM, routing with timing, suppliers, etc.)
"""


from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import copy
import json
import os



# =============================================================================
# Manufacturing routing with timing (hours)
# =============================================================================


ROUTING = [
    {
        "operationId": "OP10_FRAME_PREP",
        "sequence": 10,
        "description": "Frame preparation",
        "requiredComponents": ["BOGIE_FRAME_Y32"],
        "duration_hours": 4,
        "cumulative_start_hours": 0,
        "cumulative_end_hours": 4,
    },
    {
        "operationId": "OP20_WHEELSET_MOUNT",
        "sequence": 20,
        "description": "Wheelset and axle box assembly",
        "requiredComponents": ["WHEELSET_920MM", "AXLE_BOX"],
        "duration_hours": 8,
        "cumulative_start_hours": 4,
        "cumulative_end_hours": 12,
    },
    {
        "operationId": "OP30_SUSPENSION",
        "sequence": 30,
        "description": "Suspension installation",
        "requiredComponents": ["SUSPENSION_SPRING"],
        "duration_hours": 6,
        "cumulative_start_hours": 12,
        "cumulative_end_hours": 18,
    },
    {
        "operationId": "OP40_BRAKE_ASSEMBLY",
        "sequence": 40,
        "description": "Brake assembly",
        "requiredComponents": ["BRAKE_DISC"],
        "duration_hours": 8,
        "cumulative_start_hours": 18,
        "cumulative_end_hours": 26,
    },
    {
        "operationId": "OP50_TRACTION_MOTOR",
        "sequence": 50,
        "description": "Traction motor installation",
        "requiredComponents": ["TRACTION_MOTOR_TM"],
        "duration_hours": 8,
        "cumulative_start_hours": 26,
        "cumulative_end_hours": 34,
    },
    {
        "operationId": "OP60_TESTING",
        "sequence": 60,
        "description": "Testing and quality control",
        "requiredComponents": [],
        "duration_hours": 6,
        "cumulative_start_hours": 34,
        "cumulative_end_hours": 40,
    },
]


WORK_HOURS_PER_DAY = 8  # 8 productive hours per working day



# =============================================================================
# BOM — Bill of materials
# =============================================================================


BOM_FULL = [
    {"itemCode": "BOGIE_FRAME_Y32",  "description": "Welded Y32 bogie frame",          "qtyPerUnit": 1, "isCritical": True},
    {"itemCode": "WHEELSET_920MM",   "description": "Mounted wheelset Ø920mm",          "qtyPerUnit": 2, "isCritical": True},
    {"itemCode": "AXLE_BOX",         "description": "Axle box",                         "qtyPerUnit": 4, "isCritical": False},
    {"itemCode": "SUSPENSION_SPRING","description": "Primary suspension spring",        "qtyPerUnit": 4, "isCritical": False},
    {"itemCode": "BRAKE_DISC",       "description": "Brake disc",                       "qtyPerUnit": 4, "isCritical": True},
    {"itemCode": "TRACTION_MOTOR_TM","description": "Traction motor",                   "qtyPerUnit": 2, "isCritical": True},
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
# Suppliers
# =============================================================================


SUPPLIERS_DATA = [
    {"supplierId": "SUP-KNORR",      "name": "Knorr-Bremse",           "email": "commercial@knorr-bremse.com",   "components": ["BRAKE_DISC"],        "leadTime_days": 5,  "reliability": 0.85, "unitPrice_eur": 320,   "minOrderQty": 8},
    {"supplierId": "SUP-FAIVELEY",   "name": "Faiveley Transport",     "email": "commandes@faiveley.com",        "components": ["BRAKE_DISC"],        "leadTime_days": 3,  "reliability": 0.95, "unitPrice_eur": 380,   "minOrderQty": 4},
    {"supplierId": "SUP-ALSTOM-INT", "name": "Alstom Internal Supply", "email": "supply.internal@alstom.com",    "components": ["TRACTION_MOTOR_TM"], "leadTime_days": 10, "reliability": 0.90, "unitPrice_eur": 12000, "minOrderQty": 1},
    {"supplierId": "SUP-GHH",        "name": "GHH-Bonatrans",          "email": "orders@ghh-bonatrans.com",      "components": ["WHEELSET_920MM"],    "leadTime_days": 14, "reliability": 0.92, "unitPrice_eur": 8500,  "minOrderQty": 2},
]


HISTORICAL_OFS_DATA = [
    {"of_id": "of-2025-00087", "quantity": 2, "daysLate": 3, "wasPartialRelease": True,  "blockedComponents": ["BRAKE_DISC"],                       "blockedAtStep": "OP40"},
    {"of_id": "of-2025-00112", "quantity": 4, "daysLate": 0, "wasPartialRelease": False, "blockedComponents": [],                                   "blockedAtStep": None},
    {"of_id": "of-2025-00148", "quantity": 6, "daysLate": 4, "wasPartialRelease": True,  "blockedComponents": ["BRAKE_DISC", "TRACTION_MOTOR_TM"], "blockedAtStep": "OP40"},
    {"of_id": "of-2026-00015", "quantity": 3, "daysLate": 0, "wasPartialRelease": False, "blockedComponents": [],                                   "blockedAtStep": None},
    {"of_id": "of-2026-00058", "quantity": 4, "daysLate": 3, "wasPartialRelease": True,  "blockedComponents": ["BRAKE_DISC"],                       "blockedAtStep": "OP40"},
]


MACHINE_CALENDAR_DATA = [
    {"slotId": "SLOT-2026-03-12-AM", "date": "2026-03-12", "shift": "Morning (06:00–14:00)",   "availableHours": 8, "currentLoad": 0.30, "status": "available"},
    {"slotId": "SLOT-2026-03-12-PM", "date": "2026-03-12", "shift": "Afternoon (14:00–22:00)", "availableHours": 0, "currentLoad": 1.00, "status": "maintenance"},
    {"slotId": "SLOT-2026-03-13-AM", "date": "2026-03-13", "shift": "Morning (06:00–14:00)",   "availableHours": 8, "currentLoad": 0.20, "status": "available"},
    {"slotId": "SLOT-2026-03-13-PM", "date": "2026-03-13", "shift": "Afternoon (14:00–22:00)", "availableHours": 8, "currentLoad": 0.40, "status": "available"},
    {"slotId": "SLOT-2026-03-14-AM", "date": "2026-03-14", "shift": "Morning (06:00–14:00)",   "availableHours": 8, "currentLoad": 0.50, "status": "available"},
    {"slotId": "SLOT-2026-03-14-PM", "date": "2026-03-14", "shift": "Afternoon (14:00–22:00)", "availableHours": 8, "currentLoad": 0.35, "status": "available"},
    {"slotId": "SLOT-2026-03-17-AM", "date": "2026-03-17", "shift": "Morning (06:00–14:00)",   "availableHours": 8, "currentLoad": 0.60, "status": "available"},
    {"slotId": "SLOT-2026-03-26-AM", "date": "2026-03-26", "shift": "Morning (06:00–14:00)",   "availableHours": 8, "currentLoad": 0.10, "status": "available"},
]


SLA_RULES_DATA = [
    {"client": "SNCF_TGV", "serviceLevelAgreement": "Premium",  "maxAcceptableDelay_days": 2, "penaltyPerDayLate_eur": 5000},
    {"client": "DEFAULT",  "serviceLevelAgreement": "Standard", "maxAcceptableDelay_days": 5, "penaltyPerDayLate_eur": 1500},
]



# =============================================================================
# Seed data — 3 scenarios
# =============================================================================


def build_seed_orders() -> Dict[str, Dict]:
    """Returns the 3 demonstration production orders indexed by of_id."""
    return {
        # ── OK scenario ──────────────────────────────────────────
        "of-2026-00200": {
            "of_id": "of-2026-00200",
            "scenario": "OK",
            "scenario_label": "✅ OK scenario — Sufficient stock, no risk",
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
        # ── Medium scenario ──────────────────────────────────────
        "of-2026-00201": {
            "of_id": "of-2026-00201",
            "scenario": "Medium",
            "scenario_label": "⚠️ Medium scenario — Missing part, tight ETA",
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
                "BRAKE_DISC": 0,       # ← missing
                "TRACTION_MOTOR_TM": 9,
            },
            "historical_risk": "MEDIUM",
        },
        # ── Critical scenario ───────────────────────────────────
        "of-2026-00202": {
            "of_id": "of-2026-00202",
            "scenario": "Critical",
            "scenario_label": "🛑 Critical scenario — Major blockage risk",
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
                "WHEELSET_920MM": 4,    # ← missing (required 12)
                "AXLE_BOX": 24,
                "SUSPENSION_SPRING": 24,
                "BRAKE_DISC": 0,        # ← missing (required 24)
                "TRACTION_MOTOR_TM": 2, # ← missing (required 12)
            },
            "historical_risk": "HIGH",
        },
    }



# =============================================================================
# Helpers — production analysis
# =============================================================================


def _check_availability(components, quantity, stock):
    """Calculates missing components."""
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
    """Finds the first operation blocked by a missing component."""
    missing_codes = {mc["itemCode"] for mc in missing_components}
    for op in operations:
        if set(op.get("requiredComponents", [])) & missing_codes:
            return op
    return None



def _find_last_doable(operations, cutoff_op):
    """Last feasible operation before the cutoff."""
    if cutoff_op is None:
        return None
    cutoff_seq = cutoff_op["sequence"]
    doable = [op for op in operations if op["sequence"] < cutoff_seq]
    return doable[-1] if doable else None



def _find_risk_steps(missing_components):
    """For each missing component, finds the step that consumes it and the time to reach it."""
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
    """Builds a simulated supplier email."""
    return {
        "to": f"{supplier['email']}",
        "to_name": supplier["name"],
        "supplier_id": supplier["supplierId"],
        "subject": f"[URGENT] Order {item_code} × {qty} — {of_number}",
        "body": (
            f"Hello,\n\n"
            f"As part of {of_number}, we have an urgent need for "
            f"{qty} unit(s) of {item_code}.\n\n"
            f"Current stock: 0 / Requirement: {qty}\n"
            f"Requested delivery date: {delivery_date}\n"
            f"Impact if delayed: blockage at step {risk_step_op}\n\n"
            f"Please confirm availability and delivery lead time.\n\n"
            f"Best regards,\n"
            f"Maestro System — Alstom AI Planning"
        ),
    }



# =============================================================================
# Maestro — Simulated outputs by scenario
# =============================================================================


_SIMULATED_MAESTRO = {
    "OK": {
        "risk_level": "VERT",
        "global_risk_score": 8,
        "recommended_action": "LANCER_IMMEDIAT",
        "recommended_launch_date": "2026-03-12",
        "recommended_launch_slot": "SLOT-2026-03-12-AM",
        "estimated_production_days": 5,
        # ── Delay risk ──
        "probabilite_blocage_pct": 0,
        "estimated_delay_days": 0,
        "estimated_penalty_eur": 0,
        "etape_a_risque": None,
        # ── Messages ──
        "maestro_message": (
            "All components are available in sufficient quantities for the full routing. "
            "No blockage risk at any step. No delay expected; proceed as planned."
        ),
        "reasoning": (
            "Full stock verified across all 6 components. Comfortable buffer of about 27 days before "
            "the due date. History shows no recent blockage on this type of production order. "
            "The 12/03 morning slot is available (30% load). "
            "Recommendation: launch production immediately."
        ),
        "risk_factors": [
            {"factor": "Stock",      "score": 5,  "detail": "All components available"},
            {"factor": "History",    "score": 10, "detail": "No recent delays"},
            {"factor": "Due date",   "score": 5,  "detail": "27 days of buffer"},
            {"factor": "Schedule",   "score": 15, "detail": "Open capacity slots"},
        ],
        "supplier_order_plan": [],
        "simulated_emails": [],
        "rescheduling_options": [],
        "sla_impact": "No SLA risk — delivery well ahead of the due date.",
    },
    "Medium": {
        "risk_level": "ORANGE",
        "global_risk_score": 55,
        "recommended_action": "LANCER_DECALE",
        "recommended_launch_date": "2026-03-13",
        "recommended_launch_slot": "SLOT-2026-03-13-AM",
        "estimated_production_days": 5,
        # ── Delay risk ──
        "probabilite_blocage_pct": 30,
        "estimated_delay_days": 0,
        "estimated_penalty_eur": 0,
        "etape_a_risque": {
            "operationId": "OP40_BRAKE_ASSEMBLY",
            "sequence": 40,
            "description": "Brake assembly",
            "time_to_reach_days": 2.25,
            "composant_manquant": "BRAKE_DISC",
        },
        # ── Messages ──
        "maestro_message": (
            "The BRAKE_DISC component is missing from stock. It is consumed at step OP40 "
            "(Brake assembly), which production will reach after about 2.25 days. "
            "The supplier Faiveley Transport can deliver within 3 days. "
            "If we launch tomorrow morning (13/03), production will reach OP40 on 15/03 in the afternoon, "
            "and the brake discs will be delivered by 15/03 at the latest. This is tight but realistic. "
            "Keep a close eye on the supplier confirmation."
        ),
        "reasoning": (
            "BRAKE_DISC missing (required 16, stock 0). Consumed at OP40 (seq. 40), "
            "step reached after 18 production hours, i.e. about 2.25 working days. "
            "Best supplier: Faiveley Transport (95% reliability, 3-day lead time). "
            "If launched immediately → reaches OP40 on 14/03 in the afternoon, brake discs delivered on 15/03 → "
            "0.5 day of potential waiting. If launch is delayed to 13/03 morning → reaches OP40 on "
            "15/03 in the afternoon, brake discs delivered on 15/03 → timing aligned. "
            "History: 3–4 days of delay on similar production orders blocked by BRAKE_DISC."
        ),
        "risk_factors": [
            {"factor": "Missing critical component", "score": 75, "detail": "BRAKE_DISC absent, consumed at OP40"},
            {"factor": "Part vs. step timing",      "score": 50, "detail": "Supplier ETA (3d) ≈ time to reach OP40 (2.25d)"},
            {"factor": "Delay history",             "score": 55, "detail": "3–4 days of historical delay on BRAKE_DISC"},
            {"factor": "Due date / SLA",            "score": 40, "detail": "13 days remaining, €5,000/day penalty beyond +2 days"},
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
                "subject": "[URGENT] Order BRAKE_DISC × 16 — OF-2026-00201",
                "body": (
                    "Hello,\n\n"
                    "As part of OF-2026-00201 (4 Y32 bogies), we have an urgent need "
                    "for 16 brake discs (BRAKE_DISC).\n\n"
                    "Current stock: 0 / Requirement: 16\n"
                    "Requested delivery date: 15/03/2026\n"
                    "Impact if delayed: blockage at step OP40 (Brake assembly)\n\n"
                    "Please confirm availability and delivery lead time.\n\n"
                    "Best regards,\n"
                    "Maestro System — Alstom AI Planning"
                ),
            },
        ],
        "rescheduling_options": [],
        "sla_impact": (
            "If the BRAKE_DISC arrive within 3 days, the production order remains within SLA. "
            "Beyond that, the penalty is €5,000/day."
        ),
    },
    "Critical": {
        "risk_level": "ROUGE",
        "global_risk_score": 92,
        "recommended_action": "REPORTER_ET_REPLANIFIER",
        "recommended_launch_date": None,
        "recommended_launch_slot": None,
        "estimated_production_days": 5,
        # ── Delay risk ──
        "probabilite_blocage_pct": 95,
        "estimated_delay_days": 10,
        "estimated_penalty_eur": 50000,
        "etape_a_risque": {
            "operationId": "OP20_WHEELSET_MOUNT",
            "sequence": 20,
            "description": "Wheelset and axle box assembly",
            "time_to_reach_days": 0.5,
            "composant_manquant": "WHEELSET_920MM",
        },
        # ── Messages ──
        "maestro_message": (
            "3 critical components are missing: WHEELSET_920MM, BRAKE_DISC, TRACTION_MOTOR_TM. "
            "The first blockage (WHEELSET) occurs at OP20, reached in only 4 hours (0.5 day). "
            "The fastest supplier for WHEELSET (GHH-Bonatrans) has a 14-day lead time. "
            "Under all realistic assumptions, production will be blocked almost immediately. "
            "Do not launch now. Two rescheduling slots are proposed."
        ),
        "reasoning": (
            "3 critical components missing:\n"
            "• WHEELSET_920MM — required 12, available 4, shortage 8 → blocks OP20 (reached in 0.5 day)\n"
            "• BRAKE_DISC — required 24, available 0, shortage 24 → blocks OP40 (reached in 2.25 days)\n"
            "• TRACTION_MOTOR_TM — required 12, available 2, shortage 10 → blocks OP50 (reached in 3.25 days)\n"
            "Longest replenishment: WHEELSET_920MM (14 days via GHH-Bonatrans). "
            "Due date in 8 days: delay of 8–10 days is almost certain. "
            "Estimated penalties: €5,000/day × 10 days = €50,000."
        ),
        "risk_factors": [
            {"factor": "Missing critical components", "score": 95, "detail": "3 critical parts unavailable"},
            {"factor": "Part vs. step timing",        "score": 98, "detail": "OP20 reached in 0.5 day, parts delivered in 14 days"},
            {"factor": "Delay history",               "score": 85, "detail": "7 days of historical stock waiting"},
            {"factor": "Due date / SLA",              "score": 95, "detail": "8 days remaining, 14-day replenishment — delay certain"},
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
                "subject": "[URGENT] Order WHEELSET_920MM × 8 — OF-2026-00202",
                "body": (
                    "Hello,\n\n"
                    "As part of OF-2026-00202 (6 Y32 bogies), we have an urgent need "
                    "for 8 mounted wheelsets (WHEELSET_920MM).\n\n"
                    "Current stock: 4 / Requirement: 12\n"
                    "Requested delivery date: 26/03/2026\n"
                    "Impact if delayed: blockage at step OP20 (Wheelset assembly)\n\n"
                    "Please confirm availability and delivery lead time.\n\n"
                    "Best regards,\n"
                    "Maestro System — Alstom AI Planning"
                ),
            },
            {
                "to": "commandes@faiveley.com",
                "to_name": "Faiveley Transport",
                "supplier_id": "SUP-FAIVELEY",
                "subject": "[URGENT] Order BRAKE_DISC × 24 — OF-2026-00202",
                "body": (
                    "Hello,\n\n"
                    "As part of OF-2026-00202 (6 Y32 bogies), we have an urgent need "
                    "for 24 brake discs (BRAKE_DISC).\n\n"
                    "Current stock: 0 / Requirement: 24\n"
                    "Requested delivery date: 15/03/2026\n"
                    "Impact if delayed: blockage at step OP40 (Brake assembly)\n\n"
                    "Please confirm availability and delivery lead time.\n\n"
                    "Best regards,\n"
                    "Maestro System — Alstom AI Planning"
                ),
            },
            {
                "to": "supply.internal@alstom.com",
                "to_name": "Alstom Internal Supply",
                "supplier_id": "SUP-ALSTOM-INT",
                "subject": "[URGENT] Order TRACTION_MOTOR_TM × 10 — OF-2026-00202",
                "body": (
                    "Hello,\n\n"
                    "As part of OF-2026-00202 (6 Y32 bogies), we have an urgent need "
                    "for 10 traction motors (TRACTION_MOTOR_TM).\n\n"
                    "Current stock: 2 / Requirement: 12\n"
                    "Requested delivery date: 22/03/2026\n"
                    "Impact if delayed: blockage at step OP50 (Traction motor)\n\n"
                    "Please confirm availability and delivery lead time.\n\n"
                    "Best regards,\n"
                    "Maestro System — Alstom AI Planning"
                ),
            },
        ],
        "rescheduling_options": [
            {
                "label": "Slot A — Launch on 26/03 morning",
                "slot": "SLOT-2026-03-26-AM",
                "launch_date": "2026-03-26",
                "estimated_completion": "2026-03-31",
                "delay_client_days": 11,
                "penalty_eur": 55000,
                "comment": "All parts available. 11-day delay.",
            },
            {
                "label": "Slot B — Launch on 22/03 (partial risk)",
                "slot": "SLOT-2026-03-22-AM",
                "launch_date": "2026-03-22",
                "estimated_completion": "2026-03-28",
                "delay_client_days": 8,
                "penalty_eur": 40000,
                "comment": (
                    "BRAKE_DISC and MOTOR available, WHEELSET expected on 26/03. "
                    "Risk of blockage at OP20 on 22/03 if WHEELSET is delayed."
                ),
            },
        ],
        "sla_impact": (
            "SLA compromised — due date 20/03, full replenishment estimated at 14 days. "
            "Penalties: €5,000/day × 10+ days = €50,000+."
        ),
    },
}



# =============================================================================
# Maestro — run
# =============================================================================


def run_maestro(of_id: str, orders: Dict) -> Dict:
    """Maestro analyzes the production order and produces a launch recommendation."""
    order = orders[of_id]
    scenario = order["scenario"]
    components = order["components"]
    quantity = order["quantity"]
    stock = order["stock"]


    # --- Deterministic analysis ---
    missing = _check_availability(components, quantity, stock)
    cutoff_op = _find_cutoff(ROUTING, missing)
    last_doable = _find_last_doable(ROUTING, cutoff_op)
    risk_steps = _find_risk_steps(missing)


    # --- Simulated AI ---
    ai = _SIMULATED_MAESTRO[scenario]


    # Days until due date
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
        # ── Risk ──
        "risk_level": ai["risk_level"],
        "global_risk_score": ai["global_risk_score"],
        "probabilite_blocage_pct": ai["probabilite_blocage_pct"],
        "etape_a_risque": ai["etape_a_risque"],
        "risk_steps": risk_steps,
        # ── Launch ──
        "recommended_action": ai["recommended_action"],
        "recommended_launch_date": ai["recommended_launch_date"],
        "recommended_launch_slot": ai["recommended_launch_slot"],
        "estimated_production_days": ai["estimated_production_days"],
        # ── Delay ──
        "days_until_due": days_until_due,
        "estimated_delay_days": ai["estimated_delay_days"],
        "estimated_penalty_eur": ai["estimated_penalty_eur"],
        # ── Messages ──
        "maestro_message": ai["maestro_message"],
        "reasoning": ai["reasoning"],
        "risk_factors": ai["risk_factors"],
        "sla_impact": ai["sla_impact"],
        # ── Supplier plan ──
        "supplier_order_plan": ai["supplier_order_plan"],
        "simulated_emails": ai["simulated_emails"],
        # ── Rescheduling (if critical) ──
        "rescheduling_options": ai["rescheduling_options"],
        # ── Components ──
        "missing_components": missing,
        "cutoff_operation": {
            "operationId": cutoff_op["operationId"],
            "sequence": cutoff_op["sequence"],
            "description": cutoff_op["description"],
        } if cutoff_op else None,
        # ── Internal status ──
        "operator_decision": None,
        "previous_status": order["status"],
    }


    # Intermediate status: awaiting decision
    output["new_status"] = "AwaitingDecision"
    order["status"] = "AwaitingDecision"
    order["last_agent"] = "Maestro"


    return output



# =============================================================================
# Operator decision
# =============================================================================


def apply_operator_decision(of_id: str, orders: Dict, maestro_outputs: Dict,
                            decision: str) -> str:
    """Applies the operator's decision to a production order analyzed by Maestro."""
    order = orders[of_id]
    output = maestro_outputs[of_id]
    output["operator_decision"] = decision


    status_map = {
        "LANCER_IMMEDIAT": "Released",
        "LANCER_DECALE": "UnderMonitoring",
        "REPORTER_ET_REPLANIFIER": "Rescheduled",
    }
    new_status = status_map.get(decision, "AwaitingDecision")
    output["new_status"] = new_status
    order["status"] = new_status
    order["last_agent"] = "Operator"


    missing = output.get("missing_components", [])


    if decision == "LANCER_IMMEDIAT":
        if not missing:
            instruction = "Full production — all components are available. Launch immediately."
        else:
            shortage = ", ".join(f"{mc['itemCode']} (shortage {mc['qtyShortage']})" for mc in missing)
            instruction = (
                f"⚠️ Immediate launch by operator decision despite missing components: {shortage}. "
                f"Risk of blockage in production."
            )
    elif decision == "LANCER_DECALE":
        slot = output.get("recommended_launch_slot", "?")
        date_str = output.get("recommended_launch_date", "?")
        shortage = ", ".join(mc["itemCode"] for mc in missing) if missing else "—"
        instruction = (
            f"Launch planned for {date_str} (slot {slot}). "
            f"Monitor the arrival of: {shortage}. "
            f"Sentinelle activated for continuous follow-up."
        )
    else:  # REPORTER_ET_REPLANIFIER
        options = output.get("rescheduling_options", [])
        if options:
            opt = options[0]
            instruction = (
                f"Production order postponed. Proposed rescheduling slot: {opt['label']}. "
                f"Estimated customer delay: +{opt['delay_client_days']} days. "
                f"Sentinelle activated for supplier follow-up."
            )
        else:
            critical = [mc["itemCode"] for mc in missing if mc.get("isCritical")]
            instruction = (
                f"Production order postponed — missing critical components: {', '.join(critical) if critical else 'N/A'}. "
                f"Awaiting rescheduling."
            )


    output["instruction"] = instruction
    return instruction













# # =============================================================================
# # Orchestrateur
# # =============================================================================

# # Statuts pour lesquels le risque est considéré comme levé
# _SAFE_STATUSES = {"RisqueLeve", "Released", "ReadyToResume", "Good", "RiskCleared"}


# def run_orchestrator(maestro_outputs: Dict, orders: Dict) -> List[Dict]:
#     """Scanne les outputs Maestro et retourne la watchlist pour Sentinelle.
#     Ne garde que les OF dont le risque est encore actif."""
#     watchlist = []
#     for of_id, output in maestro_outputs.items():
#         op_decision = output.get("operator_decision")
#         order = orders.get(of_id, {})
#         # Ne pas ajouter les OF dont le risque est déjà levé
#         if order.get("status") in _SAFE_STATUSES:
#             continue
#         if op_decision in ("LANCER_DECALE", "REPORTER_ET_REPLANIFIER"):
#             watchlist.append({
#                 "of_id": of_id,
#                 "status": output["new_status"],
#                 "productCode": output["productCode"],
#                 "decision": op_decision,
#                 "risk_level": output.get("risk_level", "?"),
#                 "days_until_due": output.get("days_until_due", "?"),
#                 "etape_a_risque": output.get("etape_a_risque", {}).get("operationId", "—") if output.get("etape_a_risque") else "—",
#             })
#     return watchlist


# def refresh_watchlist(orders: Dict, current_watchlist: List[Dict]) -> List[Dict]:
#     """Recalcule la watchlist — retire les OF dont le risque est levé.
#     Appelée après chaque run de Sentinelle."""
#     new_watchlist = []
#     for entry in current_watchlist:
#         of_id = entry["of_id"]
#         order = orders.get(of_id, {})
#         if order.get("status") not in _SAFE_STATUSES:
#             new_watchlist.append(entry)
#     return new_watchlist


# # =============================================================================
# # Sentinelle — Outputs simulés
# # =============================================================================

# _SIMULATED_STOCK_SENTINELLE = {
#     "Moyen": {
#         "BRAKE_DISC": 20,  # Livraison reçue
#     },
#     "Critique": {
#         "WHEELSET_920MM": 4,
#         "BRAKE_DISC": 0,
#         "TRACTION_MOTOR_TM": 2,
#     },
# }

# _SIMULATED_SENTINELLE = {
#     "Moyen": {
#         "initial_risk_level": "ORANGE",
#         "current_risk_level": "VERT",
#         "risk_evolution": "BAISSE",
#         "warning_status": "LEVE",
#         "sentinelle_message": (
#             "Bonne nouvelle : les BRAKE_DISC ont été reçus (20 unités, livraison Faiveley confirmée). "
#             "Le risque de blocage à l'étape OP40 est désormais levé. "
#             "La production peut se poursuivre normalement jusqu'à la fin de la gamme."
#         ),
#         "parts_tracking": [
#             {
#                 "itemCode": "BRAKE_DISC",
#                 "initial_status": "MANQUANT",
#                 "current_status": "REÇU",
#                 "supplier": "Faiveley Transport",
#                 "eta_initial": "2026-03-15",
#                 "eta_updated": "2026-03-14",
#                 "qty_received": 20,
#             },
#         ],
#         "updated_eta_end": "2026-03-18",
#         "updated_delay_days": 0,
#         "resume_priority": 1,
#         "resume_priority_reasoning": "Pièces disponibles, aucun risque résiduel. Reprise immédiate recommandée.",
#         "plan_b_needed": False,
#         "rescheduling_proposal": None,
#         "supplier_recommendations": [],
#     },
#     "Critique": {
#         "initial_risk_level": "ROUGE",
#         "current_risk_level": "ROUGE",
#         "risk_evolution": "STABLE",
#         "warning_status": "CONFIRME",
#         "sentinelle_message": (
#             "Aucune amélioration : les 3 composants critiques sont toujours manquants. "
#             "Le risque de blocage est confirmé. "
#             "WHEELSET_920MM attendu le 26/03 (GHH-Bonatrans), "
#             "TRACTION_MOTOR_TM attendu le 22/03 (Alstom Internal), "
#             "BRAKE_DISC attendu le 15/03 (Faiveley). "
#             "Retard client confirmé : +10 jours minimum."
#         ),
#         "parts_tracking": [
#             {
#                 "itemCode": "WHEELSET_920MM",
#                 "initial_status": "MANQUANT",
#                 "current_status": "EN_ATTENTE",
#                 "supplier": "GHH-Bonatrans",
#                 "eta_initial": "2026-03-26",
#                 "eta_updated": "2026-03-26",
#                 "qty_received": 0,
#             },
#             {
#                 "itemCode": "BRAKE_DISC",
#                 "initial_status": "MANQUANT",
#                 "current_status": "EN_ATTENTE",
#                 "supplier": "Faiveley Transport",
#                 "eta_initial": "2026-03-15",
#                 "eta_updated": "2026-03-15",
#                 "qty_received": 0,
#             },
#             {
#                 "itemCode": "TRACTION_MOTOR_TM",
#                 "initial_status": "MANQUANT",
#                 "current_status": "EN_ATTENTE",
#                 "supplier": "Alstom Internal Supply",
#                 "eta_initial": "2026-03-22",
#                 "eta_updated": "2026-03-22",
#                 "qty_received": 0,
#             },
#         ],
#         "updated_eta_end": "2026-03-31",
#         "updated_delay_days": 11,
#         "resume_priority": 5,
#         "resume_priority_reasoning": (
#             "3 pièces critiques toujours manquantes. Pas de livraison reçue. "
#             "Prioriser d'autres OF moins bloqués."
#         ),
#         "plan_b_needed": True,
#         "rescheduling_proposal": {
#             "label": "Lancer le 26/03 matin (toutes pièces attendues)",
#             "slot": "SLOT-2026-03-26-AM",
#             "launch_date": "2026-03-26",
#             "estimated_completion": "2026-03-31",
#             "delay_client_days": 11,
#             "penalty_eur": 55000,
#         },
#         "supplier_recommendations": [
#             {
#                 "itemCode": "BRAKE_DISC",
#                 "recommended_supplier": "SUP-FAIVELEY",
#                 "supplier_name": "Faiveley Transport",
#                 "supplier_score": 91,
#                 "order_qty": 24,
#                 "unit_price_eur": 380,
#                 "total_price_eur": 9120,
#                 "estimated_lead_days": 3,
#                 "predicted_eta": "2026-03-15",
#                 "confidence": 0.92,
#             },
#             {
#                 "itemCode": "WHEELSET_920MM",
#                 "recommended_supplier": "SUP-GHH",
#                 "supplier_name": "GHH-Bonatrans",
#                 "supplier_score": 85,
#                 "order_qty": 8,
#                 "unit_price_eur": 8500,
#                 "total_price_eur": 68000,
#                 "estimated_lead_days": 14,
#                 "predicted_eta": "2026-03-26",
#                 "confidence": 0.78,
#             },
#             {
#                 "itemCode": "TRACTION_MOTOR_TM",
#                 "recommended_supplier": "SUP-ALSTOM-INT",
#                 "supplier_name": "Alstom Internal Supply",
#                 "supplier_score": 80,
#                 "order_qty": 10,
#                 "unit_price_eur": 12000,
#                 "total_price_eur": 120000,
#                 "estimated_lead_days": 10,
#                 "predicted_eta": "2026-03-22",
#                 "confidence": 0.82,
#             },
#         ],
#     },
# }


# # =============================================================================
# # Sentinelle — run
# # =============================================================================

# def get_stock_updates_preview(orders: Dict, maestro_outputs: Dict, watchlist: List[Dict]) -> List[Dict]:
#     """Aperçu des pièces qui arriveraient si Sentinelle était lancée maintenant.
#     Basé sur le temps simulé et les délais fournisseurs."""
#     previews = []
#     for entry in watchlist:
#         of_id = entry["of_id"]
#         order = orders[of_id]
#         a1 = maestro_outputs.get(of_id, {})
#         simulated_days = order.get("simulated_days", 0)
#         received_parts = order.get("received_parts", set())

#         arrivals = []
#         for plan in a1.get("supplier_order_plan", []):
#             item = plan["itemCode"]
#             if item in received_parts:
#                 continue  # déjà reçu lors d'un précédent run
#             if simulated_days >= plan["estimated_lead_days"]:
#                 arrivals.append({
#                     "itemCode": item,
#                     "stock_avant": order["stock"].get(item, 0),
#                     "stock_après": order["stock"].get(item, 0) + plan["order_qty"],
#                     "delta": plan["order_qty"],
#                     "type": "📦 Livraison",
#                 })
#             else:
#                 days_remaining = plan["estimated_lead_days"] - simulated_days
#                 arrivals.append({
#                     "itemCode": item,
#                     "stock_avant": order["stock"].get(item, 0),
#                     "stock_après": order["stock"].get(item, 0),
#                     "delta": 0,
#                     "type": f"⏳ Attendu dans {days_remaining}j",
#                 })

#         previews.append({
#             "of_id": of_id,
#             "orderNumber": order["orderNumber"],
#             "has_arrivals": any(a["delta"] > 0 for a in arrivals),
#             "arrivals": arrivals,
#         })
#     return previews


# def run_sentinelle(orders: Dict, maestro_outputs: Dict, watchlist: List[Dict]) -> List[Dict]:
#     """Sentinelle surveille les hypothèses Maestro et met à jour le risque.

#     C'est le SEUL point de contrôle de disponibilité des pièces.
#     Compare la date simulée courante aux délais fournisseurs pour décider
#     si les pièces sont arrivées ou non.
#     """
#     results = []
#     now = datetime.now(timezone.utc).isoformat()

#     for entry in watchlist:
#         of_id = entry["of_id"]
#         order = orders[of_id]
#         a1 = maestro_outputs.get(of_id, {})
#         missing_from_maestro = a1.get("missing_components", [])

#         simulated_days = order.get("simulated_days", 0)
#         # received_parts garde la trace des pièces déjà comptabilisées
#         received_parts = order.get("received_parts", set())

#         # Vérifier l'arrivée de chaque commande fournisseur
#         newly_arrived = []
#         still_waiting_plans = []
#         for plan in a1.get("supplier_order_plan", []):
#             item = plan["itemCode"]
#             if item in received_parts:
#                 continue  # déjà reçu, ne pas re-compter
#             if simulated_days >= plan["estimated_lead_days"]:
#                 newly_arrived.append(plan)
#                 received_parts.add(item)
#                 # Mise à jour du stock
#                 order["stock"][item] = (
#                     order["stock"].get(item, 0) + plan["order_qty"]
#                 )
#             else:
#                 still_waiting_plans.append(plan)

#         order["received_parts"] = received_parts

#         # Recalculer les manquants avec le stock mis à jour
#         missing_now = _check_availability(order["components"], order["quantity"], order["stock"])

#         # Tracking pièces
#         parts_tracking = []
#         for plan in a1.get("supplier_order_plan", []):
#             item = plan["itemCode"]
#             if item in received_parts:
#                 parts_tracking.append({
#                     "itemCode": item,
#                     "initial_status": "MANQUANT",
#                     "current_status": "REÇU",
#                     "supplier": plan["supplier_name"],
#                     "eta_initial": plan["predicted_eta"],
#                     "eta_updated": plan["predicted_eta"],
#                     "qty_received": plan["order_qty"],
#                 })
#             else:
#                 parts_tracking.append({
#                     "itemCode": item,
#                     "initial_status": "MANQUANT",
#                     "current_status": "EN_ATTENTE",
#                     "supplier": plan["supplier_name"],
#                     "eta_initial": plan["predicted_eta"],
#                     "eta_updated": plan["predicted_eta"],
#                     "qty_received": 0,
#                 })

#         # Résolutions et encore manquants
#         resolved = []
#         still_missing = []
#         for mc in missing_from_maestro:
#             available = order["stock"].get(mc["itemCode"], 0)
#             if available >= mc["qtyNeeded"]:
#                 resolved.append({
#                     "itemCode": mc["itemCode"],
#                     "qtyNeeded": mc["qtyNeeded"],
#                     "qtyAvailableNow": available,
#                 })
#             else:
#                 still_missing.append({
#                     "itemCode": mc["itemCode"],
#                     "qtyNeeded": mc["qtyNeeded"],
#                     "qtyAvailableNow": available,
#                     "qtyStillShort": mc["qtyNeeded"] - available,
#                     "isCritical": mc.get("isCritical", False),
#                 })

#         initial_risk = a1.get("risk_level", "?")

#         # Déterminer le statut de risque dynamiquement
#         if not missing_now:
#             new_status = "RisqueLeve"
#             warning_status = "LEVE"
#             current_risk_level = "VERT"
#             risk_evolution = "BAISSE"
#             arrived_names = ", ".join(
#                 p["itemCode"] for p in a1.get("supplier_order_plan", [])
#                 if p["itemCode"] in received_parts
#             )
#             message = (
#                 f"Bonne nouvelle : les pièces sont arrivées ({arrived_names}). "
#                 f"Le risque de blocage est désormais levé. "
#                 f"L'OF repasse au vert, la production peut se poursuivre normalement."
#             )
#         else:
#             still_missing_items = ", ".join(m["itemCode"] for m in missing_now)
#             if newly_arrived:
#                 arrived_names = ", ".join(p["itemCode"] for p in newly_arrived)
#                 new_status = "EnSurveillance"
#                 warning_status = "EN_SURVEILLANCE"
#                 current_risk_level = "ORANGE"
#                 risk_evolution = "BAISSE"
#                 message = (
#                     f"Certaines pièces sont arrivées ({arrived_names}), "
#                     f"mais il manque encore : {still_missing_items}. "
#                     f"Le risque reste actif. L'OF reste dans la watchlist."
#                 )
#             else:
#                 # Aucune nouvelle arrivée
#                 hours_elapsed = simulated_days * WORK_HOURS_PER_DAY
#                 cutoff = _find_cutoff(ROUTING, missing_now)
#                 if cutoff and hours_elapsed >= cutoff["cumulative_start_hours"]:
#                     new_status = "RisqueConfirme"
#                     warning_status = "CONFIRME"
#                     current_risk_level = "ROUGE"
#                     risk_evolution = "HAUSSE" if initial_risk != "ROUGE" else "STABLE"
#                     message = (
#                         f"Les pièces ne sont pas encore arrivées. "
#                         f"La production a atteint l'étape critique {cutoff['operationId']} "
#                         f"({cutoff['description']}). "
#                         f"Risque de blocage confirmé. Manquants : {still_missing_items}."
#                     )
#                 elif cutoff:
#                     remaining_hours = cutoff["cumulative_start_hours"] - hours_elapsed
#                     remaining_days = round(remaining_hours / WORK_HOURS_PER_DAY, 1)
#                     new_status = "EnSurveillance"
#                     warning_status = "EN_SURVEILLANCE"
#                     current_risk_level = initial_risk
#                     risk_evolution = "STABLE"
#                     message = (
#                         f"Toujours pas de réception des pièces manquantes ({still_missing_items}). "
#                         f"Attention, l'étape critique {cutoff['operationId']} approche "
#                         f"(dans {remaining_days} jour(s) de production). "
#                         f"Le risque reste actif. L'OF reste dans la watchlist."
#                     )
#                 else:
#                     new_status = "EnSurveillance"
#                     warning_status = "EN_SURVEILLANCE"
#                     current_risk_level = initial_risk
#                     risk_evolution = "STABLE"
#                     message = (
#                         f"Toujours pas de réception. "
#                         f"Pièces manquantes : {still_missing_items}. Le risque reste actif."
#                     )

#         # Estimer le retard mis à jour
#         updated_delay = 0 if not missing_now else a1.get("estimated_delay_days", 0)

#         output = {
#             "of_id": of_id,
#             "previous_status": order["status"],
#             "new_status": new_status,
#             "timestamp": now,
#             "initial_risk_level": initial_risk,
#             "current_risk_level": current_risk_level,
#             "risk_evolution": risk_evolution,
#             "warning_status": warning_status,
#             "sentinelle_message": message,
#             "parts_tracking": parts_tracking,
#             "resolved_components": resolved,
#             "still_missing_components": still_missing,
#             "stock_arrivals": [],
#             "updated_eta_end": None,
#             "updated_delay_days": updated_delay,
#             "resume_priority": 1 if not missing_now else 5,
#             "resume_priority_reasoning": (
#                 "Pièces disponibles, aucun risque résiduel. Reprise immédiate recommandée."
#                 if not missing_now else
#                 f"Pièces manquantes : {', '.join(m['itemCode'] for m in missing_now)}. En attente."
#             ),
#             "plan_b_needed": len(still_missing) > 0,
#             "rescheduling_proposal": (a1.get("rescheduling_options") or [None])[0] if still_missing else None,
#             "supplier_recommendations": [],
#         }

#         # Instruction
#         if new_status == "RisqueLeve":
#             parts = ", ".join(r["itemCode"] for r in resolved)
#             output["instruction"] = (
#                 f"✅ Risque levé — pièces reçues ({parts}). "
#                 f"Production peut continuer normalement."
#             )
#         else:
#             shortage = ", ".join(
#                 f"{sm['itemCode']} (manque {sm['qtyStillShort']})" for sm in still_missing
#             )
#             output["instruction"] = f"⏳ Risque confirmé — manquants : {shortage}."

#         # Mise à jour statut OF
#         order["status"] = new_status
#         order["last_agent"] = "Sentinelle"

#         results.append(output)

#     return results


# def resume_of(of_id: str, orders: Dict) -> None:
#     """Passe un OF en Released (reprise production — plan B worst case)."""
#     order = orders.get(of_id)
#     if order:
#         order["status"] = "Released"
#         order["last_agent"] = "Reprise"


# # =============================================================================
# # Simulation temporelle — Avancer dans le temps
# # =============================================================================

# def advance_time(of_id: str, orders: Dict, maestro_outputs: Dict,
#                  days: int = 1) -> Dict:
#     """Avance la date simulée de N jours pour un OF.

#     Responsabilité :
#       - avancer la date simulée (simulated_days += days)
#       - faire progresser la production dans les étapes
#       - recalculer la proximité du risque

#     Ne doit PAS :
#       - changer la disponibilité des pièces
#       - lever le risque
#       - retirer l'OF de la watchlist
#     """
#     order = orders[of_id]
#     m_out = maestro_outputs.get(of_id, {})

#     # Cumul des jours simulés
#     prev_days = order.get("simulated_days", 0)
#     total_days = prev_days + days
#     order["simulated_days"] = total_days

#     hours_elapsed = total_days * WORK_HOURS_PER_DAY

#     # Étape atteinte dans la production
#     current_op = ROUTING[0]
#     completed_ops = []
#     for op in ROUTING:
#         if hours_elapsed >= op["cumulative_end_hours"]:
#             completed_ops.append(op["operationId"])
#             current_op = op
#         elif hours_elapsed >= op["cumulative_start_hours"]:
#             current_op = op
#             break

#     # Vérifier la proximité du risque (sans changer le stock)
#     missing_now = _check_availability(order["components"], order["quantity"], order["stock"])
#     cutoff_now = _find_cutoff(ROUTING, missing_now)

#     blocked = False
#     blocked_at = None
#     days_remaining_to_risk = None

#     if cutoff_now:
#         hours_to_cutoff = cutoff_now["cumulative_start_hours"]
#         hours_remaining = max(0, hours_to_cutoff - hours_elapsed)
#         days_remaining_to_risk = round(hours_remaining / WORK_HOURS_PER_DAY, 1)
#         if hours_elapsed >= hours_to_cutoff:
#             blocked = True
#             blocked_at = cutoff_now

#     # Pièces en attente (infos fournisseurs, sans modifier le stock)
#     waiting_parts = []
#     for plan in m_out.get("supplier_order_plan", []):
#         item = plan["itemCode"]
#         received = order.get("received_parts", set())
#         if item not in received:
#             days_remaining_part = max(0, plan["estimated_lead_days"] - total_days)
#             waiting_parts.append({
#                 "itemCode": item,
#                 "qty_ordered": plan["order_qty"],
#                 "supplier": plan["supplier_name"],
#                 "eta_days": plan["estimated_lead_days"],
#                 "days_remaining": days_remaining_part,
#             })

#     # Construire le message (la timeline avance, pas les pièces)
#     if not missing_now:
#         message = (
#             f"La production avance normalement (J+{total_days}). "
#             f"Toutes les pièces sont déjà disponibles. Aucun risque de blocage."
#         )
#     elif blocked:
#         missing_items = ", ".join(m["itemCode"] for m in missing_now)
#         message = (
#             f"⚠️ La production a atteint l'étape {blocked_at['operationId']} "
#             f"({blocked_at['description']}) à J+{total_days}. "
#             f"Les pièces manquantes ({missing_items}) ne sont toujours pas arrivées. "
#             f"Lancez Sentinelle pour vérifier l'état des livraisons."
#         )
#     else:
#         message = (
#             f"La production avance (J+{total_days}). "
#             f"Le point de consommation critique ({cutoff_now['operationId']}) "
#             f"sera atteint dans {days_remaining_to_risk} jour(s) de production. "
#             f"Lancez Sentinelle pour vérifier si les pièces sont arrivées."
#         )

#     return {
#         "of_id": of_id,
#         "days_advanced": total_days,
#         "days_increment": days,
#         "hours_elapsed": hours_elapsed,
#         "current_operation": current_op["operationId"],
#         "current_operation_desc": current_op["description"],
#         "completed_operations": completed_ops,
#         "message": message,
#         "missing_components": missing_now,
#         "blocked": blocked,
#         "blocked_at": {
#             "operationId": blocked_at["operationId"],
#             "description": blocked_at["description"],
#         } if blocked_at else None,
#         "days_remaining_to_risk": days_remaining_to_risk,
#         "waiting_parts": waiting_parts,
#     }


# # Garde un alias pour compatibilité
# def simulate_time_advance(of_id, orders, maestro_outputs,
#                           days_advance, parts_arrive=True):
#     """Déprécié — utiliser advance_time() à la place."""
#     return advance_time(of_id, orders, maestro_outputs, days=days_advance)


# def apply_email_action(maestro_output: Dict, email_idx: int,
#                         action: str, modified_body: str = None) -> Dict:
#     """Applique une action sur un email fournisseur.

#     action: 'envoyer' | 'modifier' | 'annuler'
#     Retourne le mail mis à jour.
#     """
#     emails = maestro_output.get("simulated_emails", [])
#     if email_idx >= len(emails):
#         return {}

#     email = emails[email_idx]

#     if action == "envoyer":
#         email["status"] = "envoyé"
#         email["action_label"] = "✅ Envoyé"
#     elif action == "modifier":
#         email["status"] = "modifié"
#         email["action_label"] = "✏️ Modifié et envoyé"
#         if modified_body:
#             email["body"] = modified_body
#     elif action == "annuler":
#         email["status"] = "annulé"
#         email["action_label"] = "❌ Annulé"

#     return email


# def apply_rescheduling_choice(of_id: str, orders: Dict, maestro_outputs: Dict,
#                               option_idx: int) -> str:
#     """Applique le choix de reprogrammation de l'utilisateur.

#     Retourne un message récapitulatif.
#     """
#     m_out = maestro_outputs.get(of_id, {})
#     options = m_out.get("rescheduling_options", [])

#     if option_idx < 0 or option_idx >= len(options):
#         return "Option invalide."

#     chosen = options[option_idx]
#     m_out["chosen_rescheduling"] = chosen
#     m_out["recommended_launch_date"] = chosen["launch_date"]
#     m_out["estimated_delay_days"] = chosen["delay_client_days"]
#     m_out["estimated_penalty_eur"] = chosen["penalty_eur"]

#     order = orders[of_id]
#     order["status"] = "Replanifié"
#     order["last_agent"] = "Opérateur (replanification)"

#     comment = chosen.get("comment", "")
#     return (
#         f"Vous avez choisi de lancer le **{chosen['launch_date']}** ({chosen['label']}). "
#         f"L'IA estime un retard de **{chosen['delay_client_days']} jour(s)** "
#         f"et des pénalités de **{chosen['penalty_eur']:,.0f} €**. "
#         f"{comment} Décision enregistrée."
#     )


# # =============================================================================
# # LLM — Prompts et appel
# # =============================================================================

# MAESTRO_SYSTEM_PROMPT = """Tu es Maestro, expert en planification de production ferroviaire (Alstom).

# Tu analyses un Ordre de Fabrication (OF) pour anticiper les risques de blocage en production.
# La question clé : "Si je lance maintenant, y a-t-il un risque réaliste que la production
# atteigne une étape avant que les pièces nécessaires n'arrivent ?"

# Pour chaque OF, tu produis :
# 1. Un niveau de risque : VERT (aucun risque) / ORANGE (risque mais gérable) / ROUGE (blocage quasi certain)
# 2. Un score de risque (0-100)
# 3. Une recommandation : LANCER_IMMEDIAT, LANCER_DECALE (avec date/créneau), ou REPORTER_ET_REPLANIFIER
# 4. Le temps de traversée jusqu'à l'étape à risque vs l'ETA des pièces
# 5. Un plan de commande fournisseur si nécessaire
# 6. Une explication métier détaillée en français

# Réponds en JSON valide :
# {
#   "risk_level": "VERT | ORANGE | ROUGE",
#   "global_risk_score": <0-100>,
#   "recommended_action": "LANCER_IMMEDIAT | LANCER_DECALE | REPORTER_ET_REPLANIFIER",
#   "recommended_launch_date": "<YYYY-MM-DD ou null>",
#   "etape_a_risque": {"operationId": "...", "time_to_reach_days": <float>, "composant_manquant": "..."},
#   "probabilite_blocage_pct": <0-100>,
#   "estimated_delay_days": <number>,
#   "maestro_message": "<message clair pour le planificateur>",
#   "reasoning": "<explication détaillée>",
#   "risk_factors": [{"factor": "...", "score": <0-100>, "detail": "..."}],
#   "supplier_order_plan": [{"itemCode": "...", "supplier_name": "...", "order_qty": ..., "estimated_lead_days": ..., "predicted_eta": "..."}]
# }"""

# SENTINELLE_SYSTEM_PROMPT = """Tu es Sentinelle, agent de surveillance pour l'industrie ferroviaire (Alstom).

# Tu surveilles les OF pour lesquels Maestro a identifié un risque. Tu mets à jour en continu :
# - Le niveau de risque (VERT / ORANGE / ROUGE)
# - L'avancement des livraisons fournisseurs
# - L'impact sur la date de fin et le retard client

# Ton objectif n'est pas de gérer les blocages, mais de lever les warnings quand les hypothèses
# se confirment : "On a reçu les pièces dans les temps, le risque est levé."

# En cas critique, tu proposes des créneaux alternatifs de reprogrammation.

# Réponds en JSON valide :
# {
#   "initial_risk_level": "...",
#   "current_risk_level": "...",
#   "risk_evolution": "BAISSE | STABLE | HAUSSE",
#   "warning_status": "LEVE | CONFIRME | EN_SURVEILLANCE",
#   "sentinelle_message": "<message clair>",
#   "parts_tracking": [{"itemCode": "...", "current_status": "REÇU|EN_ATTENTE", "eta_updated": "..."}],
#   "updated_delay_days": <number>,
#   "plan_b_needed": <bool>,
#   "rescheduling_proposal": {"launch_date": "...", "delay_client_days": ...} | null
# }"""


# def build_live_context_maestro(
#     of_data: Dict, stock: Dict, missing: List,
#     cutoff_op, last_doable,
# ) -> str:
#     """Construit le prompt contextuel pour Maestro."""
#     components = BOM_FULL
#     quantity = of_data["quantity"]
#     missing_codes = {mc["itemCode"] for mc in missing}

#     lines = [
#         "# Analyse de planification OF — Maestro", "",
#         "## OF en cours",
#         f"- ID : {of_data['of_id']}",
#         f"- Produit : {of_data['productCode']}",
#         f"- Quantité : {quantity}",
#         f"- Priorité : {of_data['priority']}",
#         f"- Échéance : {of_data['dueDate']}",
#         "", "## BOM — Composants",
#     ]
#     for comp in components:
#         needed = comp["qtyPerUnit"] * quantity
#         avail = stock.get(comp["itemCode"], 0)
#         crit = "🔴 CRITIQUE" if comp.get("isCritical") else "⚪"
#         icon = "✅" if avail >= needed else "❌"
#         lines.append(f"- {icon} {comp['itemCode']} ({crit}) — besoin {needed}, dispo {avail}")

#     lines += ["", "## Gamme de fabrication avec timing"]
#     for op in ROUTING:
#         blocked = set(op.get("requiredComponents", [])) & missing_codes
#         icon = "🔴 BLOQUÉ" if blocked else "🟢 OK"
#         days = round(op["cumulative_start_hours"] / WORK_HOURS_PER_DAY, 1)
#         lines.append(
#             f"- séq.{op['sequence']} {op['operationId']} — {icon} "
#             f"(atteint en {days}j, durée {op['duration_hours']}h)"
#         )

#     if missing:
#         lines += ["", "## Composants manquants et étapes à risque"]
#         risk_steps = _find_risk_steps(missing)
#         for rs in risk_steps:
#             flag = " ⚠️ CRITIQUE" if rs.get("isCritical") else ""
#             lines.append(
#                 f"- {rs['itemCode']}{flag} — bloque {rs['operationId']} "
#                 f"(atteint en {rs['time_to_reach_days']}j), manque {rs['qtyShortage']}"
#             )

#     lines += ["", "## Fournisseurs disponibles"]
#     for sup in SUPPLIERS_DATA:
#         relevant = set(sup.get("components", [])) & missing_codes
#         if relevant:
#             lines.append(
#                 f"- {sup['name']} ({sup['supplierId']}) — {', '.join(relevant)} "
#                 f"— délai {sup['leadTime_days']}j, fiabilité {sup['reliability']*100:.0f}%"
#             )

#     lines += ["", "## Historique des OF similaires"]
#     for rec in HISTORICAL_OFS_DATA:
#         late = f"{rec['daysLate']}j retard" if rec["daysLate"] > 0 else "à l'heure"
#         blk = f", bloqué à {rec['blockedAtStep']}" if rec["blockedAtStep"] else ""
#         lines.append(f"- {rec['of_id']} — qty {rec['quantity']}, {late}{blk}")

#     lines += ["", "## Créneaux machine disponibles"]
#     for slot in MACHINE_CALENDAR_DATA:
#         if slot["status"] == "available":
#             lines.append(
#                 f"- {slot['slotId']} — {slot['date']} {slot['shift']} "
#                 f"— charge {slot['currentLoad']*100:.0f}%"
#             )

#     lines += ["", "## Règles SLA"]
#     for rule in SLA_RULES_DATA:
#         lines.append(
#             f"- Client {rule['client']} ({rule['serviceLevelAgreement']}) "
#             f"— retard max {rule['maxAcceptableDelay_days']}j, pénalité {rule['penaltyPerDayLate_eur']}€/j"
#         )

#     return "\n".join(lines)


# def build_live_context_sentinelle(
#     of_id: str, of_priority: str, of_due_date: str,
#     maestro_state: Dict, stock: Dict,
#     still_missing: List, resolved: List,
# ) -> str:
#     """Construit le prompt contextuel pour Sentinelle."""
#     lines = [
#         "# Surveillance OF — Sentinelle", "",
#         "## OF concerné",
#         f"- ID : {of_id}",
#         f"- Priorité : {of_priority}",
#         f"- Échéance : {of_due_date}",
#         f"- Risque Maestro : {maestro_state.get('risk_level', '?')} (score {maestro_state.get('global_risk_score', '?')}/100)",
#     ]
#     etape = maestro_state.get("etape_a_risque")
#     if etape:
#         lines.append(f"- Étape à risque : {etape.get('operationId', '?')} (atteint en {etape.get('time_to_reach_days', '?')}j)")

#     if resolved:
#         lines += ["", "## Composants revenus en stock ✅"]
#         for r in resolved:
#             lines.append(f"- {r['itemCode']} — dispo {r['qtyAvailableNow']} ≥ besoin {r['qtyNeeded']}")

#     if still_missing:
#         lines += ["", "## Composants toujours manquants ❌"]
#         for sm in still_missing:
#             crit = " ⚠️ CRITIQUE" if sm.get("isCritical") else ""
#             lines.append(f"- {sm['itemCode']}{crit} — besoin {sm['qtyNeeded']}, dispo {sm['qtyAvailableNow']}, manque {sm['qtyStillShort']}")

#         missing_codes = {sm["itemCode"] for sm in still_missing}
#         lines += ["", "## Fournisseurs"]
#         for sup in SUPPLIERS_DATA:
#             relevant = set(sup.get("components", [])) & missing_codes
#             if relevant:
#                 lines.append(f"- {sup['name']} — {', '.join(relevant)} — délai {sup['leadTime_days']}j")

#     lines += ["", "## SLA"]
#     for rule in SLA_RULES_DATA:
#         lines.append(f"- {rule['client']} — retard max {rule['maxAcceptableDelay_days']}j, pénalité {rule['penaltyPerDayLate_eur']}€/j")

#     return "\n".join(lines)


# def _extract_json_from_response(response: str) -> Optional[Dict]:
#     """Extrait le JSON d'une réponse LLM."""
#     try:
#         if "```json" in response:
#             start = response.index("```json") + 7
#             end = response.index("```", start)
#             return json.loads(response[start:end].strip())
#         start = response.find("{")
#         if start >= 0:
#             end = response.rfind("}")
#             return json.loads(response[start:end + 1])
#     except (json.JSONDecodeError, ValueError):
#         pass
#     return None


# def call_llm(instructions: str, context: str):
#     """Appel synchrone au LLM Azure AI Foundry.

#     Returns: (parsed_json | None, raw_text, error_msg | None)
#     """
#     endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT") or os.getenv("AI_FOUNDRY_PROJECT_ENDPOINT")
#     model = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4.1")

#     if not endpoint:
#         return None, "", "Variable AZURE_AI_PROJECT_ENDPOINT non définie."

#     try:
#         from azure.ai.projects import AIProjectClient
#         from azure.identity import DefaultAzureCredential
#     except ImportError:
#         return None, "", "Packages azure-ai-projects / azure-identity non installés."

#     try:
#         client = AIProjectClient(
#             endpoint=endpoint,
#             credential=DefaultAzureCredential(),
#         )
#         response = client.inference.get_chat_completions_client().complete(
#             model=model,
#             messages=[
#                 {"role": "system", "content": instructions},
#                 {"role": "user", "content": context},
#             ],
#         )
#         raw_text = response.choices[0].message.content
#         parsed = _extract_json_from_response(raw_text)
#         return parsed, raw_text, None
#     except Exception as e:
#         return None, "", f"{type(e).__name__}: {e}"

# =============================================================================
# Orchestrator
# =============================================================================


# Statuses for which the risk is considered cleared
_SAFE_STATUSES = {"RiskCleared", "Released", "ReadyToResume", "Good", "RiskCleared"}



def run_orchestrator(maestro_outputs: Dict, orders: Dict) -> List[Dict]:
    """Scans Maestro outputs and returns the watchlist for Sentinelle.
    Keeps only production orders whose risk is still active."""
    watchlist = []
    for of_id, output in maestro_outputs.items():
        op_decision = output.get("operator_decision")
        order = orders.get(of_id, {})
        # Do not add production orders whose risk has already been cleared
        if order.get("status") in _SAFE_STATUSES:
            continue
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



def refresh_watchlist(orders: Dict, current_watchlist: List[Dict]) -> List[Dict]:
    """Recalculates the watchlist — removes production orders whose risk has been cleared.
    Called after each Sentinelle run."""
    new_watchlist = []
    for entry in current_watchlist:
        of_id = entry["of_id"]
        order = orders.get(of_id, {})
        if order.get("status") not in _SAFE_STATUSES:
            new_watchlist.append(entry)
    return new_watchlist



# =============================================================================
# Sentinelle — Simulated outputs
# =============================================================================


_SIMULATED_STOCK_SENTINELLE = {
    "Medium": {
        "BRAKE_DISC": 20,  # Delivery received
    },
    "Critical": {
        "WHEELSET_920MM": 4,
        "BRAKE_DISC": 0,
        "TRACTION_MOTOR_TM": 2,
    },
}


_SIMULATED_SENTINELLE = {
    "Medium": {
        "initial_risk_level": "ORANGE",
        "current_risk_level": "VERT",
        "risk_evolution": "BAISSE",
        "warning_status": "LEVE",
        "sentinelle_message": (
            "Good news: the BRAKE_DISC have been received (20 units, Faiveley delivery confirmed). "
            "The blockage risk at step OP40 has now been cleared. "
            "Production can continue normally through to the end of the routing."
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
        "resume_priority_reasoning": "Parts available, no residual risk. Immediate resumption recommended.",
        "plan_b_needed": False,
        "rescheduling_proposal": None,
        "supplier_recommendations": [],
    },
    "Critical": {
        "initial_risk_level": "ROUGE",
        "current_risk_level": "ROUGE",
        "risk_evolution": "STABLE",
        "warning_status": "CONFIRME",
        "sentinelle_message": (
            "No improvement: the 3 critical components are still missing. "
            "The blockage risk is confirmed. "
            "WHEELSET_920MM expected on 26/03 (GHH-Bonatrans), "
            "TRACTION_MOTOR_TM expected on 22/03 (Alstom Internal), "
            "BRAKE_DISC expected on 15/03 (Faiveley). "
            "Customer delay confirmed: +10 days minimum."
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
            "3 critical parts still missing. No delivery received. "
            "Prioritize other, less blocked production orders."
        ),
        "plan_b_needed": True,
        "rescheduling_proposal": {
            "label": "Launch on 26/03 morning (all parts expected)",
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


def get_stock_updates_preview(orders: Dict, maestro_outputs: Dict, watchlist: List[Dict]) -> List[Dict]:
    """Preview of parts that would arrive if Sentinelle were run now.
    Based on simulated time and supplier lead times."""
    previews = []
    for entry in watchlist:
        of_id = entry["of_id"]
        order = orders[of_id]
        a1 = maestro_outputs.get(of_id, {})
        simulated_days = order.get("simulated_days", 0)
        received_parts = order.get("received_parts", set())


        arrivals = []
        for plan in a1.get("supplier_order_plan", []):
            item = plan["itemCode"]
            if item in received_parts:
                continue  # already received during a previous run
            if simulated_days >= plan["estimated_lead_days"]:
                arrivals.append({
                    "itemCode": item,
                    "stock_before": order["stock"].get(item, 0),
                    "stock_after": order["stock"].get(item, 0) + plan["order_qty"],
                    "delta": plan["order_qty"],
                    "type": "📦 Delivery",
                })
            else:
                days_remaining = plan["estimated_lead_days"] - simulated_days
                arrivals.append({
                    "itemCode": item,
                    "stock_before": order["stock"].get(item, 0),
                    "stock_after": order["stock"].get(item, 0),
                    "delta": 0,
                    "type": f"⏳ Expected in {days_remaining}d",
                })


        previews.append({
            "of_id": of_id,
            "orderNumber": order["orderNumber"],
            "has_arrivals": any(a["delta"] > 0 for a in arrivals),
            "arrivals": arrivals,
        })
    return previews



def run_sentinelle(orders: Dict, maestro_outputs: Dict, watchlist: List[Dict]) -> List[Dict]:
    """Sentinelle monitors Maestro's assumptions and updates the risk.


    This is the ONLY control point for part availability.
    It compares the current simulated date with supplier lead times to decide
    whether the parts have arrived or not.
    """
    results = []
    now = datetime.now(timezone.utc).isoformat()


    for entry in watchlist:
        of_id = entry["of_id"]
        order = orders[of_id]
        a1 = maestro_outputs.get(of_id, {})
        missing_from_maestro = a1.get("missing_components", [])


        simulated_days = order.get("simulated_days", 0)
        # received_parts keeps track of parts already counted
        received_parts = order.get("received_parts", set())


        # Check the arrival of each supplier order
        newly_arrived = []
        still_waiting_plans = []
        for plan in a1.get("supplier_order_plan", []):
            item = plan["itemCode"]
            if item in received_parts:
                continue  # already received, do not count twice
            if simulated_days >= plan["estimated_lead_days"]:
                newly_arrived.append(plan)
                received_parts.add(item)
                # Stock update
                order["stock"][item] = (
                    order["stock"].get(item, 0) + plan["order_qty"]
                )
            else:
                still_waiting_plans.append(plan)


        order["received_parts"] = received_parts


        # Recalculate missing components with the updated stock
        missing_now = _check_availability(order["components"], order["quantity"], order["stock"])


        # Parts tracking
        parts_tracking = []
        for plan in a1.get("supplier_order_plan", []):
            item = plan["itemCode"]
            if item in received_parts:
                parts_tracking.append({
                    "itemCode": item,
                    "initial_status": "MANQUANT",
                    "current_status": "REÇU",
                    "supplier": plan["supplier_name"],
                    "eta_initial": plan["predicted_eta"],
                    "eta_updated": plan["predicted_eta"],
                    "qty_received": plan["order_qty"],
                })
            else:
                parts_tracking.append({
                    "itemCode": item,
                    "initial_status": "MANQUANT",
                    "current_status": "EN_ATTENTE",
                    "supplier": plan["supplier_name"],
                    "eta_initial": plan["predicted_eta"],
                    "eta_updated": plan["predicted_eta"],
                    "qty_received": 0,
                })


        # Resolved and still missing
        resolved = []
        still_missing = []
        for mc in missing_from_maestro:
            available = order["stock"].get(mc["itemCode"], 0)
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


        initial_risk = a1.get("risk_level", "?")


        # Determine risk status dynamically
        if not missing_now:
            new_status = "RiskCleared"
            warning_status = "LEVE"
            current_risk_level = "VERT"
            risk_evolution = "BAISSE"
            arrived_names = ", ".join(
                p["itemCode"] for p in a1.get("supplier_order_plan", [])
                if p["itemCode"] in received_parts
            )
            message = (
                f"Good news: the parts have arrived ({arrived_names}). "
                f"The blockage risk has now been cleared. "
                f"The production order is back to green and production can continue normally."
            )
        else:
            still_missing_items = ", ".join(m["itemCode"] for m in missing_now)
            if newly_arrived:
                arrived_names = ", ".join(p["itemCode"] for p in newly_arrived)
                new_status = "UnderMonitoring"
                warning_status = "EN_SURVEILLANCE"
                current_risk_level = "ORANGE"
                risk_evolution = "BAISSE"
                message = (
                    f"Some parts have arrived ({arrived_names}), "
                    f"but the following are still missing: {still_missing_items}. "
                    f"The risk remains active. The production order stays in the watchlist."
                )
            else:
                # No new arrival
                hours_elapsed = simulated_days * WORK_HOURS_PER_DAY
                cutoff = _find_cutoff(ROUTING, missing_now)
                if cutoff and hours_elapsed >= cutoff["cumulative_start_hours"]:
                    new_status = "RiskConfirmed"
                    warning_status = "CONFIRME"
                    current_risk_level = "ROUGE"
                    risk_evolution = "HAUSSE" if initial_risk != "ROUGE" else "STABLE"
                    message = (
                        f"The parts have still not arrived. "
                        f"Production has reached the critical step {cutoff['operationId']} "
                        f"({cutoff['description']}). "
                        f"Blockage risk confirmed. Missing: {still_missing_items}."
                    )
                elif cutoff:
                    remaining_hours = cutoff["cumulative_start_hours"] - hours_elapsed
                    remaining_days = round(remaining_hours / WORK_HOURS_PER_DAY, 1)
                    new_status = "UnderMonitoring"
                    warning_status = "EN_SURVEILLANCE"
                    current_risk_level = initial_risk
                    risk_evolution = "STABLE"
                    message = (
                        f"The missing parts have still not been received ({still_missing_items}). "
                        f"Warning: the critical step {cutoff['operationId']} is getting closer "
                        f"(in {remaining_days} production day(s)). "
                        f"The risk remains active. The production order stays in the watchlist."
                    )
                else:
                    new_status = "UnderMonitoring"
                    warning_status = "EN_SURVEILLANCE"
                    current_risk_level = initial_risk
                    risk_evolution = "STABLE"
                    message = (
                        f"Still no receipt. "
                        f"Missing parts: {still_missing_items}. The risk remains active."
                    )


        # Estimate updated delay
        updated_delay = 0 if not missing_now else a1.get("estimated_delay_days", 0)


        output = {
            "of_id": of_id,
            "previous_status": order["status"],
            "new_status": new_status,
            "timestamp": now,
            "initial_risk_level": initial_risk,
            "current_risk_level": current_risk_level,
            "risk_evolution": risk_evolution,
            "warning_status": warning_status,
            "sentinelle_message": message,
            "parts_tracking": parts_tracking,
            "resolved_components": resolved,
            "still_missing_components": still_missing,
            "stock_arrivals": [],
            "updated_eta_end": None,
            "updated_delay_days": updated_delay,
            "resume_priority": 1 if not missing_now else 5,
            "resume_priority_reasoning": (
                "Parts available, no residual risk. Immediate resumption recommended."
                if not missing_now else
                f"Missing parts: {', '.join(m['itemCode'] for m in missing_now)}. Awaiting receipt."
            ),
            "plan_b_needed": len(still_missing) > 0,
            "rescheduling_proposal": (a1.get("rescheduling_options") or [None])[0] if still_missing else None,
            "supplier_recommendations": [],
        }


        # Instruction
        if new_status == "RiskCleared":
            parts = ", ".join(r["itemCode"] for r in resolved)
            output["instruction"] = (
                f"✅ Risk cleared — parts received ({parts}). "
                f"Production can continue normally."
            )
        else:
            shortage = ", ".join(
                f"{sm['itemCode']} (short {sm['qtyStillShort']})" for sm in still_missing
            )
            output["instruction"] = f"⏳ Risk confirmed — still missing: {shortage}."


        # Update production order status
        order["status"] = new_status
        order["last_agent"] = "Sentinelle"


        results.append(output)


    return results



def resume_of(of_id: str, orders: Dict) -> None:
    """Sets a production order to Released (production resume — worst-case Plan B)."""
    order = orders.get(of_id)
    if order:
        order["status"] = "Released"
        order["last_agent"] = "Resume"



# =============================================================================
# Time simulation — Move forward in time
# =============================================================================


def advance_time(of_id: str, orders: Dict, maestro_outputs: Dict,
                 days: int = 1) -> Dict:
    """Moves the simulated date forward by N days for a production order.


    Responsibility:
      - move the simulated date forward (simulated_days += days)
      - move production forward through the steps
      - recalculate the proximity of the risk


    Must NOT:
      - change part availability
      - clear the risk
      - remove the production order from the watchlist
    """
    order = orders[of_id]
    m_out = maestro_outputs.get(of_id, {})


    # Accumulate simulated days
    prev_days = order.get("simulated_days", 0)
    total_days = prev_days + days
    order["simulated_days"] = total_days


    hours_elapsed = total_days * WORK_HOURS_PER_DAY


    # Current step reached in production
    current_op = ROUTING[0]
    completed_ops = []
    for op in ROUTING:
        if hours_elapsed >= op["cumulative_end_hours"]:
            completed_ops.append(op["operationId"])
            current_op = op
        elif hours_elapsed >= op["cumulative_start_hours"]:
            current_op = op
            break


    # Check risk proximity (without changing stock)
    missing_now = _check_availability(order["components"], order["quantity"], order["stock"])
    cutoff_now = _find_cutoff(ROUTING, missing_now)


    blocked = False
    blocked_at = None
    days_remaining_to_risk = None


    if cutoff_now:
        hours_to_cutoff = cutoff_now["cumulative_start_hours"]
        hours_remaining = max(0, hours_to_cutoff - hours_elapsed)
        days_remaining_to_risk = round(hours_remaining / WORK_HOURS_PER_DAY, 1)
        if hours_elapsed >= hours_to_cutoff:
            blocked = True
            blocked_at = cutoff_now


    # Waiting parts (supplier information, without modifying stock)
    waiting_parts = []
    for plan in m_out.get("supplier_order_plan", []):
        item = plan["itemCode"]
        received = order.get("received_parts", set())
        if item not in received:
            days_remaining_part = max(0, plan["estimated_lead_days"] - total_days)
            waiting_parts.append({
                "itemCode": item,
                "qty_ordered": plan["order_qty"],
                "supplier": plan["supplier_name"],
                "eta_days": plan["estimated_lead_days"],
                "days_remaining": days_remaining_part,
            })


    # Build the message (timeline moves forward, not the parts)
    if not missing_now:
        message = (
            f"Production is progressing normally (D+{total_days}). "
            f"All parts are already available. No blockage risk."
        )
    elif blocked:
        missing_items = ", ".join(m["itemCode"] for m in missing_now)
        message = (
            f"⚠️ Production has reached step {blocked_at['operationId']} "
            f"({blocked_at['description']}) at D+{total_days}. "
            f"The missing parts ({missing_items}) have still not arrived. "
            f"Run Sentinelle to check delivery status."
        )
    else:
        message = (
            f"Production is progressing (D+{total_days}). "
            f"The critical consumption point ({cutoff_now['operationId']}) "
            f"will be reached in {days_remaining_to_risk} production day(s). "
            f"Run Sentinelle to check whether the parts have arrived."
        )


    return {
        "of_id": of_id,
        "days_advanced": total_days,
        "days_increment": days,
        "hours_elapsed": hours_elapsed,
        "current_operation": current_op["operationId"],
        "current_operation_desc": current_op["description"],
        "completed_operations": completed_ops,
        "message": message,
        "missing_components": missing_now,
        "blocked": blocked,
        "blocked_at": {
            "operationId": blocked_at["operationId"],
            "description": blocked_at["description"],
        } if blocked_at else None,
        "days_remaining_to_risk": days_remaining_to_risk,
        "waiting_parts": waiting_parts,
    }



# Keep an alias for compatibility
def simulate_time_advance(of_id, orders, maestro_outputs,
                          days_advance, parts_arrive=True):
    """Deprecated — use advance_time() instead."""
    return advance_time(of_id, orders, maestro_outputs, days=days_advance)



def apply_email_action(maestro_output: Dict, email_idx: int,
                        action: str, modified_body: str = None) -> Dict:
    """Applies an action to a supplier email.


    action: 'envoyer' | 'modifier' | 'annuler'
    Returns the updated email.
    """
    emails = maestro_output.get("simulated_emails", [])
    if email_idx >= len(emails):
        return {}


    email = emails[email_idx]


    if action == "envoyer":
        email["status"] = "sent"
        email["action_label"] = "✅ Sent"
    elif action == "modifier":
        email["status"] = "edited"
        email["action_label"] = "✏️ Edited and sent"
        if modified_body:
            email["body"] = modified_body
    elif action == "annuler":
        email["status"] = "cancelled"
        email["action_label"] = "❌ Cancelled"


    return email



def apply_rescheduling_choice(of_id: str, orders: Dict, maestro_outputs: Dict,
                              option_idx: int) -> str:
    """Applies the user's rescheduling choice.


    Returns a summary message.
    """
    m_out = maestro_outputs.get(of_id, {})
    options = m_out.get("rescheduling_options", [])


    if option_idx < 0 or option_idx >= len(options):
        return "Invalid option."


    chosen = options[option_idx]
    m_out["chosen_rescheduling"] = chosen
    m_out["recommended_launch_date"] = chosen["launch_date"]
    m_out["estimated_delay_days"] = chosen["delay_client_days"]
    m_out["estimated_penalty_eur"] = chosen["penalty_eur"]


    order = orders[of_id]
    order["status"] = "Rescheduled"
    order["last_agent"] = "Operator (rescheduling)"


    comment = chosen.get("comment", "")
    return (
        f"You chose to launch on **{chosen['launch_date']}** ({chosen['label']}). "
        f"The AI estimates a delay of **{chosen['delay_client_days']} day(s)** "
        f"and penalties of **{chosen['penalty_eur']:,.0f} €**. "
        f"{comment} Decision recorded."
    )



# =============================================================================
# LLM — Prompts and call
# =============================================================================


MAESTRO_SYSTEM_PROMPT = """You are Maestro, an expert in railway production planning (Alstom).


You analyze a Production Order (PO) to anticipate blockage risks in production.
The key question is: "If I launch now, is there a realistic risk that production
will reach a step before the required parts arrive?"


For each production order, you produce:
1. A risk level: GREEN (no risk) / ORANGE (risk but manageable) / RED (blockage almost certain)
2. A risk score (0-100)
3. A recommendation: LANCER_IMMEDIAT, LANCER_DECALE (with date/slot), or REPORTER_ET_REPLANIFIER
4. The throughput time to the at-risk step versus the parts ETA
5. A supplier ordering plan if needed
6. A detailed business explanation in French


Respond in valid JSON:
{
  "risk_level": "VERT | ORANGE | ROUGE",
  "global_risk_score": <0-100>,
  "recommended_action": "LANCER_IMMEDIAT | LANCER_DECALE | REPORTER_ET_REPLANIFIER",
  "recommended_launch_date": "<YYYY-MM-DD or null>",
  "etape_a_risque": {"operationId": "...", "time_to_reach_days": <float>, "composant_manquant": "..."},
  "probabilite_blocage_pct": <0-100>,
  "estimated_delay_days": <number>,
  "maestro_message": "<clear message for the planner>",
  "reasoning": "<detailed explanation>",
  "risk_factors": [{"factor": "...", "score": <0-100>, "detail": "..."}],
  "supplier_order_plan": [{"itemCode": "...", "supplier_name": "...", "order_qty": ..., "estimated_lead_days": ..., "predicted_eta": "..."}]
}"""


SENTINELLE_SYSTEM_PROMPT = """You are Sentinelle, a monitoring agent for the railway industry (Alstom).


You monitor the production orders for which Maestro has identified a risk. You continuously update:
- The risk level (GREEN / ORANGE / RED)
- Supplier delivery progress
- The impact on the completion date and customer delay


Your goal is not to manage blockages, but to clear warnings when assumptions
are confirmed: "The parts were received on time, the risk is cleared."


In critical cases, you propose alternative rescheduling slots.


Respond in valid JSON:
{
  "initial_risk_level": "...",
  "current_risk_level": "...",
  "risk_evolution": "BAISSE | STABLE | HAUSSE",
  "warning_status": "LEVE | CONFIRME | EN_SURVEILLANCE",
  "sentinelle_message": "<clear message>",
  "parts_tracking": [{"itemCode": "...", "current_status": "REÇU|EN_ATTENTE", "eta_updated": "..."}],
  "updated_delay_days": <number>,
  "plan_b_needed": <bool>,
  "rescheduling_proposal": {"launch_date": "...", "delay_client_days": ...} | null
}"""



def build_live_context_maestro(
    of_data: Dict, stock: Dict, missing: List,
    cutoff_op, last_doable,
) -> str:
    """Builds the contextual prompt for Maestro."""
    components = BOM_FULL
    quantity = of_data["quantity"]
    missing_codes = {mc["itemCode"] for mc in missing}


    lines = [
        "# Production order planning analysis — Maestro", "",
        "## Current production order",
        f"- ID : {of_data['of_id']}",
        f"- Product : {of_data['productCode']}",
        f"- Quantity : {quantity}",
        f"- Priority : {of_data['priority']}",
        f"- Due date : {of_data['dueDate']}",
        "", "## BOM — Components",
    ]
    for comp in components:
        needed = comp["qtyPerUnit"] * quantity
        avail = stock.get(comp["itemCode"], 0)
        crit = "🔴 CRITICAL" if comp.get("isCritical") else "⚪"
        icon = "✅" if avail >= needed else "❌"
        lines.append(f"- {icon} {comp['itemCode']} ({crit}) — required {needed}, available {avail}")


    lines += ["", "## Manufacturing routing with timing"]
    for op in ROUTING:
        blocked = set(op.get("requiredComponents", [])) & missing_codes
        icon = "🔴 BLOCKED" if blocked else "🟢 OK"
        days = round(op["cumulative_start_hours"] / WORK_HOURS_PER_DAY, 1)
        lines.append(
            f"- seq.{op['sequence']} {op['operationId']} — {icon} "
            f"(reached in {days}d, duration {op['duration_hours']}h)"
        )


    if missing:
        lines += ["", "## Missing components and at-risk steps"]
        risk_steps = _find_risk_steps(missing)
        for rs in risk_steps:
            flag = " ⚠️ CRITICAL" if rs.get("isCritical") else ""
            lines.append(
                f"- {rs['itemCode']}{flag} — blocks {rs['operationId']} "
                f"(reached in {rs['time_to_reach_days']}d), shortage {rs['qtyShortage']}"
            )


    lines += ["", "## Available suppliers"]
    for sup in SUPPLIERS_DATA:
        relevant = set(sup.get("components", [])) & missing_codes
        if relevant:
            lines.append(
                f"- {sup['name']} ({sup['supplierId']}) — {', '.join(relevant)} "
                f"— lead time {sup['leadTime_days']}d, reliability {sup['reliability']*100:.0f}%"
            )


    lines += ["", "## History of similar production orders"]
    for rec in HISTORICAL_OFS_DATA:
        late = f"{rec['daysLate']}d late" if rec["daysLate"] > 0 else "on time"
        blk = f", blocked at {rec['blockedAtStep']}" if rec["blockedAtStep"] else ""
        lines.append(f"- {rec['of_id']} — qty {rec['quantity']}, {late}{blk}")


    lines += ["", "## Available machine slots"]
    for slot in MACHINE_CALENDAR_DATA:
        if slot["status"] == "available":
            lines.append(
                f"- {slot['slotId']} — {slot['date']} {slot['shift']} "
                f"— load {slot['currentLoad']*100:.0f}%"
            )


    lines += ["", "## SLA rules"]
    for rule in SLA_RULES_DATA:
        lines.append(
            f"- Customer {rule['client']} ({rule['serviceLevelAgreement']}) "
            f"— max delay {rule['maxAcceptableDelay_days']}d, penalty {rule['penaltyPerDayLate_eur']}€/d"
        )


    return "\n".join(lines)



def build_live_context_sentinelle(
    of_id: str, of_priority: str, of_due_date: str,
    maestro_state: Dict, stock: Dict,
    still_missing: List, resolved: List,
) -> str:
    """Builds the contextual prompt for Sentinelle."""
    lines = [
        "# Production order monitoring — Sentinelle", "",
        "## Concerned production order",
        f"- ID : {of_id}",
        f"- Priority : {of_priority}",
        f"- Due date : {of_due_date}",
        f"- Maestro risk : {maestro_state.get('risk_level', '?')} (score {maestro_state.get('global_risk_score', '?')}/100)",
    ]
    etape = maestro_state.get("etape_a_risque")
    if etape:
        lines.append(f"- At-risk step : {etape.get('operationId', '?')} (reached in {etape.get('time_to_reach_days', '?')}d)")


    if resolved:
        lines += ["", "## Components back in stock ✅"]
        for r in resolved:
            lines.append(f"- {r['itemCode']} — available {r['qtyAvailableNow']} ≥ required {r['qtyNeeded']}")


    if still_missing:
        lines += ["", "## Components still missing ❌"]
        for sm in still_missing:
            crit = " ⚠️ CRITICAL" if sm.get("isCritical") else ""
            lines.append(f"- {sm['itemCode']}{crit} — required {sm['qtyNeeded']}, available {sm['qtyAvailableNow']}, short {sm['qtyStillShort']}")


        missing_codes = {sm["itemCode"] for sm in still_missing}
        lines += ["", "## Suppliers"]
        for sup in SUPPLIERS_DATA:
            relevant = set(sup.get("components", [])) & missing_codes
            if relevant:
                lines.append(f"- {sup['name']} — {', '.join(relevant)} — lead time {sup['leadTime_days']}d")


    lines += ["", "## SLA"]
    for rule in SLA_RULES_DATA:
        lines.append(f"- {rule['client']} — max delay {rule['maxAcceptableDelay_days']}d, penalty {rule['penaltyPerDayLate_eur']}€/d")


    return "\n".join(lines)



def _extract_json_from_response(response: str) -> Optional[Dict]:
    """Extracts JSON from an LLM response."""
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
    """Synchronous call to the Azure AI Foundry LLM.


    Returns: (parsed_json | None, raw_text, error_msg | None)
    """
    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT") or os.getenv("AI_FOUNDRY_PROJECT_ENDPOINT")
    model = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4.1")


    if not endpoint:
        return None, "", "AZURE_AI_PROJECT_ENDPOINT variable is not defined."


    try:
        from azure.ai.projects import AIProjectClient
        from azure.identity import DefaultAzureCredential
    except ImportError:
        return None, "", "azure-ai-projects / azure-identity packages are not installed."


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
        raw_text = response.choices.message.content
        parsed = _extract_json_from_response(raw_text)
        return parsed, raw_text, None
    except Exception as e:
        return None, "", f"{type(e).__name__}: {e}"
