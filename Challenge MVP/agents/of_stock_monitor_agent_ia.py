#!/usr/bin/env python3
"""Agent 2 IA — Surveillance stock intelligente & reprise d'OF.

Enrichit la logique MVP (vérification pénuries) avec une couche IA :
  • Optimisation fournisseur (scoring fiabilité × délai × coût)
  • Prédiction ETA des pièces manquantes
  • Prioritisation des OF quand plusieurs OF concurrents partagent le même stock
  • Notifications contextuelles avec recommandations d'achat

Fallback automatique vers la logique MVP si Azure AI n'est pas configuré.

Usage:
    python agents/of_stock_monitor_agent_ia.py [--data-dir DATA_DIR]
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

load_dotenv(override=True)

logger = logging.getLogger(__name__)

# =============================================================================
# Chargement des données
# =============================================================================

def load_json(filepath: str) -> Any:
    with open(filepath, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def load_orders_to_watch(data_dir: str) -> List[Dict]:
    data = load_json(os.path.join(data_dir, "orders_partially_released.json"))
    # Surveiller les OF en PartiallyReleased ou Delayed (décision Agent 1 IA)
    orders = [o for o in data["orders"] if o["status"] in ("PartiallyReleased", "Delayed")]
    print(f"   {len(orders)} OF à surveiller (PartiallyReleased / Delayed)")
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
            print(f"   Agent 1 output chargé : {os.path.basename(path)}")
            if state.get("of_id") != of_id:
                raise ValueError(f"Output Agent 1 = {state.get('of_id')}, attendu {of_id}")
            return state

    raise FileNotFoundError(
        f"Aucun output Agent 1 pour {of_id} "
        f"(cherché : {', '.join(os.path.basename(p) for p in candidates)})"
    )


def load_stock(data_dir: str) -> Dict[str, int]:
    snapshot = load_json(os.path.join(data_dir, "stock_snapshot.json"))
    stock = {item["itemCode"]: item["qtyAvailable"] for item in snapshot["items"]}
    print(f"   Stock chargé : {len(stock)} références")
    return stock


def load_optional_json(data_dir: str, filename: str) -> Any:
    path = os.path.join(data_dir, filename)
    if os.path.exists(path):
        return load_json(path)
    print(f"   ℹ️  {filename} non trouvé — données optionnelles ignorées")
    return None


# =============================================================================
# Logique MVP (déterministe)
# =============================================================================

def check_shortages_resolved(
    missing_components: List[Dict], stock: Dict[str, int]
) -> Tuple[List[Dict], List[Dict]]:
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


def decide_new_status(still_missing: List[Dict]) -> str:
    return "ReadyToResume" if len(still_missing) == 0 else "PartiallyReleased"


# =============================================================================
# Couche IA — Agent de surveillance stock & approvisionnement
# =============================================================================

class OFStockMonitorAgent:
    """Agent IA pour la surveillance stock et l'optimisation des réapprovisionnements."""

    def __init__(self, project_endpoint: str, deployment_name: str):
        self.project_endpoint = project_endpoint
        self.deployment_name = deployment_name

    async def analyze(
        self,
        of_id: str,
        of_priority: str,
        of_due_date: str,
        agent1_state: Dict,
        stock: Dict[str, int],
        still_missing: List[Dict],
        resolved: List[Dict],
        suppliers_data: Any,
        parts_history: Any,
        demand_forecast: Any,
        sla_rules: Any,
    ) -> Dict:
        """Envoie le contexte au modèle IA et retourne les recommandations."""

        from agent_framework.azure import AzureAIClient
        from azure.identity.aio import AzureCliCredential

        context = self._build_context(
            of_id, of_priority, of_due_date, agent1_state, stock,
            still_missing, resolved, suppliers_data, parts_history,
            demand_forecast, sla_rules,
        )

        instructions = """Tu es un expert en gestion des approvisionnements et réapprovisionnement pour l'industrie ferroviaire (Alstom).

Pour chaque OF partiellement lancé, tu dois analyser les pénuries restantes et fournir :
1. Pour chaque composant manquant : le fournisseur optimal (score basé sur fiabilité × délai × coût),
   une prédiction d'ETA et une recommandation de commande.
2. Une priorité de reprise (resume_priority : 1 = urgent, 5 = peut attendre) basée sur
   l'échéance OF, le SLA, et les composants critiques.
3. Une notification contextuelle pour le superviseur de production.

Critères de choix fournisseur :
- Fiabilité (reliability) : poids 40%
- Délai (leadTime) : poids 35%
- Coût unitaire (unitPrice) : poids 25%

Réponds UNIQUEMENT en JSON valide."""

        async with AzureCliCredential() as credential:
            async with AzureAIClient(credential=credential).create_agent(
                name="OFStockMonitorAgent",
                description="Agent de surveillance stock et optimisation réapprovisionnement",
                instructions=instructions,
            ) as agent:
                print(f"   ✅ Agent IA créé : {agent.id}")
                result = await agent.run(context)
                response_text = result.text

        json_str = self._extract_json(response_text)
        return json.loads(json_str)

    def _build_context(
        self, of_id, of_priority, of_due_date, agent1_state, stock,
        still_missing, resolved, suppliers_data, parts_history,
        demand_forecast, sla_rules,
    ) -> str:
        lines = [
            "# Analyse de réapprovisionnement pour OF partiel",
            "",
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

        # Composants résolus
        if resolved:
            lines.append("")
            lines.append("## Composants revenus en stock ✅")
            for r in resolved:
                lines.append(f"- {r['itemCode']} — dispo {r['qtyAvailableNow']} ≥ besoin {r['qtyNeeded']}")

        # Composants toujours manquants
        if still_missing:
            lines.append("")
            lines.append("## Composants toujours manquants ❌")
            for sm in still_missing:
                crit = " ⚠️ CRITIQUE" if sm.get("isCritical") else ""
                lines.append(
                    f"- {sm['itemCode']}{crit} — besoin {sm['qtyNeeded']}, "
                    f"dispo {sm['qtyAvailableNow']}, manque {sm['qtyStillShort']}"
                )

        # Fournisseurs disponibles
        if suppliers_data and suppliers_data.get("suppliers"):
            missing_codes = {sm["itemCode"] for sm in still_missing}
            lines.append("")
            lines.append("## Fournisseurs disponibles")
            for sup in suppliers_data["suppliers"]:
                # N'afficher que les fournisseurs pertinents
                sup_components = set(sup.get("components", []))
                relevant = sup_components & missing_codes
                if relevant:
                    lines.append(f"### {sup['name']} ({sup['supplierId']})")
                    lines.append(f"- Composants : {', '.join(relevant)}")
                    lines.append(f"- Lead time : {sup['leadTime_days']} jours")
                    lines.append(f"- Fiabilité : {sup['reliability']*100:.0f}%")
                    lines.append(f"- Prix unitaire : {sup['unitPrice_eur']}€")
                    lines.append(f"- Qté min commande : {sup['minOrderQty']}")
                    if sup.get("historicalDeliveries"):
                        avg_late = sum(d.get("daysLate", 0) for d in sup["historicalDeliveries"]) / len(sup["historicalDeliveries"])
                        lines.append(f"- Retard moyen historique : {avg_late:.1f} jours")

        # Historique commandes
        if parts_history and parts_history.get("orders"):
            missing_codes = {sm["itemCode"] for sm in still_missing}
            relevant_orders = [o for o in parts_history["orders"] if o["itemCode"] in missing_codes]
            if relevant_orders:
                lines.append("")
                lines.append("## Historique commandes récentes (composants manquants)")
                for order in relevant_orders[-5:]:
                    status = order["status"]
                    late_str = ""
                    if order.get("daysLate") is not None:
                        late_str = f", {order['daysLate']}j retard" if order["daysLate"] > 0 else ", à l'heure"
                    lines.append(
                        f"- {order['orderId']} — {order['itemCode']} × {order['orderedQty']} "
                        f"via {order['supplierId']} — {status}{late_str}"
                    )
                # Commandes en transit
                in_transit = [o for o in relevant_orders if o["status"] == "in_transit"]
                if in_transit:
                    lines.append("")
                    lines.append("⚡ Commandes en transit :")
                    for o in in_transit:
                        lines.append(
                            f"  - {o['orderId']} — {o['itemCode']} × {o['orderedQty']} "
                            f"— ETA prévue : {o.get('expectedDeliveryDate', '?')}"
                            + (f" — {o.get('notes', '')}" if o.get("notes") else "")
                        )

        # Prévisions de demande
        if demand_forecast and demand_forecast.get("forecasts"):
            missing_codes = {sm["itemCode"] for sm in still_missing}
            relevant = [f for f in demand_forecast["forecasts"] if f["itemCode"] in missing_codes]
            if relevant:
                lines.append("")
                lines.append("## Prévisions de demande (composants manquants)")
                for fc in relevant:
                    lines.append(
                        f"- {fc['itemCode']} — besoin total horizon {fc['totalForecastQty']}, "
                        f"en transit {fc['inTransitQty']}, pénurie attendue {fc.get('expectedShortage', '?')} "
                        f"→ risque {fc['riskLevel']}"
                    )

        # SLA
        if sla_rules and sla_rules.get("rules"):
            lines.append("")
            lines.append("## Contraintes SLA")
            for rule in sla_rules["rules"]:
                lines.append(
                    f"- Client {rule['client']} ({rule['serviceLevelAgreement']}) — "
                    f"retard max {rule['maxAcceptableDelay_days']}j, pénalité {rule['penaltyPerDayLate_eur']}€/j"
                )

        # Réponse attendue
        lines.extend([
            "",
            "## Réponse attendue (JSON)",
            "```json",
            "{",
            '  "resume_priority": <1-5>,',
            '  "resume_priority_reasoning": "<explication>",',
            '  "supplier_recommendations": [',
            "    {",
            '      "itemCode": "<composant>",',
            '      "recommended_supplier": "<supplierId>",',
            '      "supplier_name": "<nom>",',
            '      "supplier_score": <0-100>,',
            '      "order_qty": <number>,',
            '      "unit_price_eur": <number>,',
            '      "total_price_eur": <number>,',
            '      "estimated_lead_days": <number>,',
            '      "predicted_eta": "<YYYY-MM-DD>",',
            '      "confidence": <0.0-1.0>',
            "    }",
            "  ],",
            '  "notification_text": "<message pour le superviseur en français>",',
            '  "overall_eta_days": <nombre de jours avant reprise possible>,',
            '  "risk_assessment": "<description risque global>"',
            "}",
            "```",
        ])

        return "\n".join(lines)

    def _extract_json(self, response: str) -> str:
        if "```json" in response:
            start = response.index("```json") + 7
            end = response.index("```", start)
            return response[start:end].strip()
        start = response.find("{")
        if start >= 0:
            end = response.rfind("}")
            return response[start : end + 1]
        raise Exception("Impossible d'extraire le JSON de la réponse IA")


# =============================================================================
# Construction et persistance de l'output enrichi
# =============================================================================

def build_output(
    of_id: str,
    previous_status: str,
    new_status: str,
    agent1_state: Dict,
    resolved: List[Dict],
    still_missing: List[Dict],
    ai_analysis: Optional[Dict] = None,
) -> Dict:
    output: Dict[str, Any] = {
        "of_id": of_id,
        "previous_status": previous_status,
        "new_status": new_status,
        "resolved_components": resolved,
        "still_missing_components": still_missing,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Données IA
    if ai_analysis:
        output["ai_enhanced"] = True
        output["resume_priority"] = ai_analysis.get("resume_priority")
        output["resume_priority_reasoning"] = ai_analysis.get("resume_priority_reasoning", "")
        output["supplier_recommendations"] = ai_analysis.get("supplier_recommendations", [])
        output["overall_eta_days"] = ai_analysis.get("overall_eta_days")
        output["risk_assessment"] = ai_analysis.get("risk_assessment", "")
        output["ai_notification"] = ai_analysis.get("notification_text", "")
    else:
        output["ai_enhanced"] = False

    if new_status == "ReadyToResume":
        resume_op = agent1_state.get("resume_from_operation", {})
        output["resume_from_operation"] = resume_op
        parts_list = ", ".join(
            f"{r['itemCode']} ({r['qtyNeeded']}/{r['qtyAvailableNow']})" for r in resolved
        )
        op_id = resume_op.get("operationId", "?")
        output["instruction"] = (
            f"Reprendre la production à partir de l'opération {op_id}. "
            f"Composants disponibles : {parts_list}."
        )
    else:
        shortage = ", ".join(
            f"{sm['itemCode']} (manque {sm['qtyStillShort']})" for sm in still_missing
        )
        output["instruction"] = (
            f"OF toujours en attente — composants insuffisants : {shortage}."
        )

    return output


def persist_output(output: Dict, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"   Output écrit dans : {output_path}")


def update_of_status(data_dir: str, of_id: str, new_status: str) -> None:
    of_path = os.path.join(data_dir, "of.json")
    if not os.path.exists(of_path):
        print(f"   ⚠️  of.json introuvable")
        return
    of = load_json(of_path)
    if of.get("id") == of_id:
        of["status"] = new_status
        with open(of_path, "w", encoding="utf-8") as f:
            json.dump(of, f, indent=2, ensure_ascii=False)
        print(f"   OF mis à jour : status → {new_status}")


def notify(output: Dict) -> None:
    ts = output["timestamp"]
    of_id = output["of_id"]
    new_status = output["new_status"]
    print()

    if new_status == "ReadyToResume":
        resume_op = output.get("resume_from_operation", {})
        op_id = resume_op.get("operationId", "?")
        parts = ", ".join(
            f"{r['itemCode']} ({r['qtyNeeded']}/{r['qtyAvailableNow']})"
            for r in output["resolved_components"]
        )
        print(f"   📢 NOTIFICATION [{ts}]")
        print(f"   OF {of_id} prêt à reprendre.")
        print(f"   ➜ Reprendre à partir de {op_id}.")
        print(f"   ➜ Composants disponibles : {parts}.")
    else:
        shortage = ", ".join(
            f"{sm['itemCode']} (manque {sm['qtyStillShort']})"
            for sm in output["still_missing_components"]
        )
        print(f"   ℹ️  NOTIFICATION [{ts}]")
        print(f"   OF {of_id} toujours en attente.")
        print(f"   ➜ Composants manquants : {shortage}.")

    # Notification IA enrichie
    if output.get("ai_notification"):
        print()
        print(f"   🤖 Message IA : {output['ai_notification']}")


# =============================================================================
# Affichage console enrichi
# =============================================================================

def print_summary(results: List[Dict]) -> None:
    ready = [r for r in results if r["new_status"] == "ReadyToResume"]
    waiting = [r for r in results if r["new_status"] == "PartiallyReleased"]

    print()
    print("=" * 70)
    print("  AGENT 2 IA — SURVEILLANCE STOCK & REPRISE")
    print("=" * 70)
    print(f"  OF traités           : {len(results)}")
    print(f"  ✅ Prêts à reprendre : {len(ready)}")
    print(f"  ⏳ Toujours en attente: {len(waiting)}")

    if ready:
        print()
        print("  OF prêts à reprendre :")
        for r in ready:
            op = r.get("resume_from_operation", {}).get("operationId", "?")
            print(f"    • {r['of_id']} → reprendre à {op}")

    if waiting:
        print()
        print("  OF toujours en attente :")
        for r in waiting:
            parts = ", ".join(
                f"{sm['itemCode']} (manque {sm['qtyStillShort']})"
                for sm in r["still_missing_components"]
            )
            prio = ""
            if r.get("ai_enhanced") and r.get("resume_priority"):
                prio = f" [priorité reprise : {r['resume_priority']}/5]"
            print(f"    • {r['of_id']}{prio} → {parts}")

            # Recommandations fournisseurs
            if r.get("supplier_recommendations"):
                for rec in r["supplier_recommendations"]:
                    print(
                        f"      📦 {rec.get('itemCode', '?')} → "
                        f"{rec.get('supplier_name', '?')} ({rec.get('recommended_supplier', '?')}) — "
                        f"{rec.get('order_qty', '?')} pcs, ETA {rec.get('predicted_eta', '?')}, "
                        f"{rec.get('total_price_eur', '?')}€"
                    )

            if r.get("overall_eta_days") is not None:
                print(f"      ⏱️  ETA reprise estimée : {r['overall_eta_days']} jours")

    print("=" * 70)
    print()


# =============================================================================
# Point d'entrée (async)
# =============================================================================

async def async_main(data_dir: str):
    print()
    print("🔍 Agent 2 IA — Surveillance stock & reprise OF")
    print("-" * 55)

    # ── Étape 1 : charger les OF à surveiller ─────────────────────────────
    print("[1/7] Chargement des OF en PartiallyReleased...")
    orders = load_orders_to_watch(data_dir)
    if not orders:
        print("   Aucun OF à surveiller. Fin.")
        return

    # ── Étape 2 : stock ────────────────────────────────────────────────────
    print("[2/7] Chargement du stock actuel...")
    stock = load_stock(data_dir)
    for code, qty in stock.items():
        print(f"   • {code} : {qty}")

    # ── Chargement données IA (optionnelles) ───────────────────────────────
    print("[  ] Chargement données IA (optionnelles)...")
    suppliers_data = load_optional_json(data_dir, "suppliers.json")
    parts_history = load_optional_json(data_dir, "parts_history.json")
    demand_forecast = load_optional_json(data_dir, "demand_forecast.json")
    sla_rules = load_optional_json(data_dir, "sla_rules.json")

    # Config IA
    project_endpoint = (
        os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        or os.getenv("AI_FOUNDRY_PROJECT_ENDPOINT")
    )
    deployment_name = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4.1")

    results: List[Dict] = []

    for order in orders:
        of_id = order["of_id"]
        print()
        print(f"  ┌── Traitement OF : {of_id}")

        # ── Étape 3 : output Agent 1 ──────────────────────────────────────
        print(f"  │ [3/7] Chargement output Agent 1...")
        try:
            agent1_state = load_agent1_output(
                data_dir, of_id,
                agent1_output_file=order.get("agent1_output_file"),
            )
        except (FileNotFoundError, ValueError) as e:
            print(f"  │ ⚠️  Erreur : {e}")
            print(f"  └── OF {of_id} ignoré")
            continue

        missing_components = agent1_state.get("missing_components", [])

        # ── Étape 4 : vérifier pénuries ────────────────────────────────────
        print(f"  │ [4/7] Vérification des pénuries...")
        resolved, still_missing = check_shortages_resolved(missing_components, stock)
        for r in resolved:
            print(f"  │   ✅ {r['itemCode']} — dispo {r['qtyAvailableNow']} ≥ besoin {r['qtyNeeded']}")
        for sm in still_missing:
            crit = " 🔴" if sm.get("isCritical") else ""
            print(f"  │   ❌ {sm['itemCode']}{crit} — dispo {sm['qtyAvailableNow']} < besoin {sm['qtyNeeded']}")

        # ── Étape 5 : décision ──────────────────────────────────────────────
        print(f"  │ [5/7] Prise de décision...")
        new_status = decide_new_status(still_missing)
        print(f"  │   Décision : {new_status}")

        # ── Étape 5b : analyse IA (si stock toujours manquant & IA dispo) ──
        ai_analysis = None
        if still_missing and project_endpoint:
            print(f"  │ [5b] 🤖 Analyse IA des recommandations fournisseur...")
            try:
                # Récupérer priorité et échéance de l'OF depuis of.json ou l'order
                of_priority = order.get("priority", "N/A")
                of_due_date = order.get("dueDate", "N/A")
                # Si pas dans order, charger depuis of.json
                if of_priority == "N/A":
                    of_path = os.path.join(data_dir, "of.json")
                    if os.path.exists(of_path):
                        of_data = load_json(of_path)
                        if of_data.get("id") == of_id:
                            of_priority = of_data.get("priority", "N/A")
                            of_due_date = of_data.get("dueDate", "N/A")

                ia_agent = OFStockMonitorAgent(project_endpoint, deployment_name)
                ai_analysis = await ia_agent.analyze(
                    of_id=of_id,
                    of_priority=of_priority,
                    of_due_date=of_due_date,
                    agent1_state=agent1_state,
                    stock=stock,
                    still_missing=still_missing,
                    resolved=resolved,
                    suppliers_data=suppliers_data,
                    parts_history=parts_history,
                    demand_forecast=demand_forecast,
                    sla_rules=sla_rules,
                )
                print(f"  │   IA → priorité reprise : {ai_analysis.get('resume_priority', '?')}/5")
                print(f"  │   IA → ETA reprise : {ai_analysis.get('overall_eta_days', '?')} jours")
            except Exception as e:
                print(f"  │   ⚠️  Erreur IA : {e}")
                print(f"  │   Fallback → mode MVP uniquement")
        elif still_missing:
            print(f"  │ [5b] ℹ️  Azure AI non configuré — pas de recommandations fournisseur")

        # ── Étape 6 : output ────────────────────────────────────────────────
        print(f"  │ [6/7] Construction output...")
        output = build_output(
            of_id=of_id,
            previous_status=order["status"],
            new_status=new_status,
            agent1_state=agent1_state,
            resolved=resolved,
            still_missing=still_missing,
            ai_analysis=ai_analysis,
        )

        # ── Étape 7 : persister + notifier ──────────────────────────────────
        print(f"  │ [7/7] Persistance, notification & mise à jour...")
        output_path = os.path.join(data_dir, f"agent2_output_{of_id}.json")
        persist_output(output, output_path)
        if new_status == "ReadyToResume":
            update_of_status(data_dir, of_id, new_status)
        notify(output)

        results.append(output)
        print(f"  └── OF {of_id} traité")

    print_summary(results)


def main():
    parser = argparse.ArgumentParser(description="Agent 2 IA — Surveillance stock & reprise OF")
    parser.add_argument(
        "--data-dir",
        default=os.path.join(os.path.dirname(__file__), "..", "data"),
        help="Répertoire contenant les fichiers de données",
    )
    args = parser.parse_args()
    data_dir = os.path.abspath(args.data_dir)
    asyncio.run(async_main(data_dir))


if __name__ == "__main__":
    main()
