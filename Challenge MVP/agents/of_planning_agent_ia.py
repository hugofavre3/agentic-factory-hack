#!/usr/bin/env python3
"""Agent 1 IA — Planification intelligente d'Ordre de Fabrication (OF).

Enrichit la logique MVP (BOM vs stock) avec une couche IA :
  • Score de risque global (0-100) basé sur l'historique, la BOM critique, les SLA
  • Décision 3 voies : FULL_RELEASE / PARTIAL_RELEASE / DELAYED_RELEASE
  • Recommandation de créneau machine optimal
  • Explication générée par l'IA

Fallback automatique vers la logique MVP si Azure AI n'est pas configuré.

Usage:
    python agents/of_planning_agent_ia.py [--data-dir DATA_DIR] [--output PATH]
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv(override=True)

logger = logging.getLogger(__name__)

# =============================================================================
# Chargement des données
# =============================================================================

def load_json(filepath: str) -> Any:
    """Charge et parse un fichier JSON."""
    with open(filepath, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def load_of(data_dir: str) -> Dict:
    of = load_json(os.path.join(data_dir, "of.json"))
    print(f"   OF chargé : {of['id']} — produit {of['productCode']} × {of['quantity']}")
    return of


def load_bom_and_routing(data_dir: str, product_code: str):
    bom = load_json(os.path.join(data_dir, "bom.json"))
    routing = load_json(os.path.join(data_dir, "routing.json"))
    if bom["productCode"] != product_code:
        raise ValueError(f"BOM productCode ({bom['productCode']}) ≠ OF ({product_code})")
    if routing["productCode"] != product_code:
        raise ValueError(f"Routing productCode ({routing['productCode']}) ≠ OF ({product_code})")
    components = bom["components"]
    operations = sorted(routing["operations"], key=lambda op: op["sequence"])
    print(f"   BOM chargée : {len(components)} composants")
    print(f"   Gamme chargée : {len(operations)} opérations")
    return components, operations


def load_stock(data_dir: str) -> Dict[str, int]:
    snapshot = load_json(os.path.join(data_dir, "stock_snapshot.json"))
    stock = {item["itemCode"]: item["qtyAvailable"] for item in snapshot["items"]}
    print(f"   Stock chargé : {len(stock)} références")
    return stock


def load_optional_json(data_dir: str, filename: str) -> Any:
    """Charge un fichier JSON optionnel, retourne None s'il est absent."""
    path = os.path.join(data_dir, filename)
    if os.path.exists(path):
        return load_json(path)
    print(f"   ℹ️  {filename} non trouvé — données optionnelles ignorées")
    return None


# =============================================================================
# Logique MVP (déterministe)
# =============================================================================

def check_availability(components: List[Dict], of_qty: int, stock: Dict[str, int]) -> List[Dict]:
    missing: List[Dict] = []
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


def decide_mvp(missing_components: List[Dict]) -> str:
    return "FULL_RELEASE" if len(missing_components) == 0 else "PARTIAL_RELEASE"


def find_cutoff_operation(operations: List[Dict], missing_components: List[Dict]) -> Optional[Dict]:
    missing_codes = {mc["itemCode"] for mc in missing_components}
    for op in operations:
        if set(op.get("requiredComponents", [])) & missing_codes:
            return op
    return None


def find_last_doable_operation(operations: List[Dict], cutoff_op: Optional[Dict]) -> Optional[Dict]:
    if cutoff_op is None:
        return None
    cutoff_seq = cutoff_op["sequence"]
    doable = [op for op in operations if op["sequence"] < cutoff_seq]
    return doable[-1] if doable else None


# =============================================================================
# Couche IA — Agent de planification OF
# =============================================================================

class OFPlanningAgent:
    """Agent IA pour la planification enrichie des OF."""

    def __init__(self, project_endpoint: str, deployment_name: str):
        self.project_endpoint = project_endpoint
        self.deployment_name = deployment_name

    async def analyze(
        self,
        of: Dict,
        components: List[Dict],
        operations: List[Dict],
        stock: Dict[str, int],
        missing_components: List[Dict],
        mvp_decision: str,
        cutoff_op: Optional[Dict],
        last_doable_op: Optional[Dict],
        historical_ofs: Any,
        machine_calendar: Any,
        sla_rules: Any,
        demand_forecast: Any,
    ) -> Dict:
        """Envoie le contexte complet à l'IA et retourne la décision enrichie."""

        # Import Azure AI (lazy — uniquement si cette méthode est appelée)
        from agent_framework.azure import AzureAIClient
        from azure.identity.aio import AzureCliCredential

        context = self._build_context(
            of, components, operations, stock, missing_components,
            mvp_decision, cutoff_op, last_doable_op,
            historical_ofs, machine_calendar, sla_rules, demand_forecast,
        )

        instructions = """Tu es un expert en planification de production ferroviaire (Alstom).

Analyse le contexte d'un Ordre de Fabrication (OF) et fournis :
1. Un score de risque global (0-100) et un niveau de risque (HIGH / MEDIUM / LOW)
2. Une décision parmi : FULL_RELEASE, PARTIAL_RELEASE, DELAYED_RELEASE
3. Un créneau machine recommandé pour démarrer la production
4. Une explication métier détaillée en français

Critères de décision :
- FULL_RELEASE : tout est disponible, risque faible, créneau OK
- PARTIAL_RELEASE : des composants manquent mais on peut avancer partiellement
  (la production jusqu'au cutoff apporte de la valeur et le délai de réapprovisionnement est acceptable)
- DELAYED_RELEASE : les composants critiques (isCritical=true) manquent,
  le risque SLA est trop élevé, ou le créneau machine est inadapté.
  Il vaut mieux attendre que lancer partiellement.

Réponds UNIQUEMENT en JSON valide."""

        # Appel IA via AzureAIClient (même pattern que maintenance_scheduler_agent)
        async with AzureCliCredential() as credential:
            async with AzureAIClient(credential=credential).create_agent(
                name="OFPlanningAgent",
                description="Agent de planification intelligente des OF ferroviaires",
                instructions=instructions,
            ) as agent:
                print(f"   ✅ Agent IA créé : {agent.id}")
                result = await agent.run(context)
                response_text = result.text

        json_str = self._extract_json(response_text)
        return json.loads(json_str)

    # ── Construction du contexte ──────────────────────────────────────────

    def _build_context(
        self, of, components, operations, stock, missing_components,
        mvp_decision, cutoff_op, last_doable_op,
        historical_ofs, machine_calendar, sla_rules, demand_forecast,
    ) -> str:
        lines = [
            "# Analyse de planification OF",
            "",
            "## OF en cours",
            f"- ID : {of['id']}",
            f"- Produit : {of['productCode']}",
            f"- Quantité : {of['quantity']}",
            f"- Priorité : {of.get('priority', 'N/A')}",
            f"- Échéance : {of.get('dueDate', 'N/A')}",
            f"- Statut actuel : {of.get('status', 'Created')}",
            "",
            "## BOM — Composants",
        ]

        for comp in components:
            qty_needed = comp["qtyPerUnit"] * of["quantity"]
            qty_avail = stock.get(comp["itemCode"], 0)
            crit = "🔴 CRITIQUE" if comp.get("isCritical") else "⚪"
            status = "✅" if qty_avail >= qty_needed else "❌"
            lines.append(
                f"- {status} {comp['itemCode']} ({crit}) — besoin {qty_needed}, dispo {qty_avail}"
            )

        lines.append("")
        lines.append("## Gamme de fabrication")
        missing_codes = {mc["itemCode"] for mc in missing_components}
        for op in operations:
            req = set(op.get("requiredComponents", []))
            blocked = req & missing_codes
            icon = "🔴 BLOQUÉ" if blocked else "🟢 OK"
            lines.append(f"- séq.{op['sequence']} {op['operationId']} — {icon}")

        lines.append("")
        lines.append("## Décision MVP (déterministe)")
        lines.append(f"- Décision : {mvp_decision}")
        if cutoff_op:
            lines.append(f"- Coupure à : {cutoff_op['operationId']} (séq. {cutoff_op['sequence']})")
        if last_doable_op:
            lines.append(f"- Dernière op réalisable : {last_doable_op['operationId']}")

        if missing_components:
            lines.append("")
            lines.append("## Composants manquants")
            for mc in missing_components:
                crit_flag = " ⚠️ CRITIQUE" if mc.get("isCritical") else ""
                lines.append(
                    f"- {mc['itemCode']}{crit_flag} — manque {mc['qtyShortage']} "
                    f"(besoin {mc['qtyNeeded']}, dispo {mc['qtyAvailable']})"
                )

        # Historique
        if historical_ofs and historical_ofs.get("records"):
            lines.append("")
            lines.append("## Historique des OF similaires")
            for rec in historical_ofs["records"][-5:]:
                late_info = f"{rec['daysLate']}j retard" if rec["daysLate"] > 0 else "à l'heure"
                partial = "partiel" if rec.get("wasPartialRelease") else "complet"
                lines.append(
                    f"- {rec['of_id']} — qty {rec['quantity']}, {partial}, {late_info}"
                    + (f", bloqué par {rec['blockedComponents']}" if rec.get("blockedComponents") else "")
                )

        # Calendrier machine
        if machine_calendar and machine_calendar.get("slots"):
            lines.append("")
            lines.append("## Créneaux machine disponibles")
            for slot in machine_calendar["slots"]:
                if slot["status"] == "available":
                    lines.append(
                        f"- {slot['slotId']} — {slot['date']} {slot['shift']} — "
                        f"charge {slot['currentLoad']*100:.0f}% — {slot['availableHours']}h dispo"
                    )
            if machine_calendar.get("unavailabilities"):
                lines.append("")
                lines.append("Indisponibilités :")
                for u in machine_calendar["unavailabilities"]:
                    lines.append(f"- {u['date']} {u['shift']} — {u['reason']}")

        # SLA
        if sla_rules and sla_rules.get("rules"):
            lines.append("")
            lines.append("## Règles SLA")
            for rule in sla_rules["rules"]:
                lines.append(
                    f"- Client {rule['client']} ({rule['serviceLevelAgreement']}) — "
                    f"retard max {rule['maxAcceptableDelay_days']}j, "
                    f"pénalité {rule['penaltyPerDayLate_eur']}€/j"
                )

        # Prévisions demande
        if demand_forecast and demand_forecast.get("forecasts"):
            lines.append("")
            lines.append("## Prévisions de demande (horizon 30j)")
            for fc in demand_forecast["forecasts"]:
                lines.append(
                    f"- {fc['itemCode']} — besoin total {fc['totalForecastQty']}, "
                    f"stock {fc['currentStock']}, en transit {fc['inTransitQty']} "
                    f"→ risque {fc['riskLevel']}"
                )

        # Réponse attendue
        lines.extend([
            "",
            "## Réponse attendue (JSON)",
            "```json",
            "{",
            '  "decision": "FULL_RELEASE | PARTIAL_RELEASE | DELAYED_RELEASE",',
            '  "global_risk_score": <0-100>,',
            '  "risk_level": "HIGH | MEDIUM | LOW",',
            '  "recommended_start_slot": "<slotId ou null>",',
            '  "reasoning": "<explication détaillée en français>",',
            '  "risk_factors": [',
            '    { "factor": "<nom>", "score": <0-100>, "detail": "<detail>" }',
            '  ],',
            '  "estimated_production_days": <number>,',
            '  "sla_impact": "<description impact SLA>"',
            "}",
            "```",
        ])

        return "\n".join(lines)

    # ── Extraction JSON ───────────────────────────────────────────────────

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
# Construction de l'output enrichi
# =============================================================================

def build_output(
    of: Dict,
    decision: str,
    missing_components: List[Dict],
    cutoff_op: Optional[Dict],
    last_doable_op: Optional[Dict],
    ai_analysis: Optional[Dict] = None,
) -> Dict:
    """Construit l'output enrichi avec les données IA (si disponibles)."""

    output: Dict[str, Any] = {
        "of_id": of["id"],
        "orderNumber": of["orderNumber"],
        "productCode": of["productCode"],
        "quantity": of["quantity"],
        "decision": decision,
        "previous_status": of.get("status", "Created"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Données IA
    if ai_analysis:
        output["ai_enhanced"] = True
        output["global_risk_score"] = ai_analysis.get("global_risk_score", 0)
        output["risk_level"] = ai_analysis.get("risk_level", "UNKNOWN")
        output["risk_factors"] = ai_analysis.get("risk_factors", [])
        output["recommended_start_slot"] = ai_analysis.get("recommended_start_slot")
        output["estimated_production_days"] = ai_analysis.get("estimated_production_days")
        output["sla_impact"] = ai_analysis.get("sla_impact", "")
        output["ai_reasoning"] = ai_analysis.get("reasoning", "")
    else:
        output["ai_enhanced"] = False

    # Statut et instruction selon la décision
    if decision == "FULL_RELEASE":
        output["new_status"] = "Released"
        output["missing_components"] = []
        output["instruction"] = (
            "Production normale — tous les composants sont disponibles."
        )

    elif decision == "PARTIAL_RELEASE":
        output["new_status"] = "PartiallyReleased"
        output["missing_components"] = missing_components
        if cutoff_op and last_doable_op:
            output["cutoff_operation"] = {
                "operationId": cutoff_op["operationId"],
                "sequence": cutoff_op["sequence"],
                "description": cutoff_op["description"],
            }
            output["resume_from_operation"] = {
                "operationId": cutoff_op["operationId"],
                "sequence": cutoff_op["sequence"],
            }
            shortage_parts = ", ".join(
                f"{mc['itemCode']} (manque {mc['qtyShortage']})" for mc in missing_components
            )
            output["instruction"] = (
                f"Produire jusqu'à {last_doable_op['operationId']} "
                f"(séq. {last_doable_op['sequence']}) inclus, "
                f"puis mettre de côté en attente de : {shortage_parts}"
            )
        else:
            output["cutoff_operation"] = None
            output["resume_from_operation"] = None
            output["instruction"] = (
                "Aucune opération réalisable — tous les composants manquent dès la première opération."
            )

    elif decision == "DELAYED_RELEASE":
        output["new_status"] = "Delayed"
        output["missing_components"] = missing_components
        output["cutoff_operation"] = None
        output["resume_from_operation"] = None
        critical_missing = [mc for mc in missing_components if mc.get("isCritical")]
        if critical_missing:
            parts_str = ", ".join(mc["itemCode"] for mc in critical_missing)
            output["instruction"] = (
                f"OF mis en attente — composants critiques manquants : {parts_str}. "
                f"Risque SLA trop élevé pour un lancement partiel."
            )
        else:
            output["instruction"] = (
                "OF mis en attente sur recommandation IA — conditions non réunies pour lancer."
            )

    return output


def persist_output(output: Dict, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"   Output écrit dans : {output_path}")


def update_of_status(data_dir: str, of: Dict, new_status: str) -> None:
    of_path = os.path.join(data_dir, "of.json")
    of["status"] = new_status
    with open(of_path, "w", encoding="utf-8") as f:
        json.dump(of, f, indent=2, ensure_ascii=False)
    print(f"   OF mis à jour : status → {new_status}")


# =============================================================================
# Affichage console enrichi
# =============================================================================

def print_summary(output: Dict) -> None:
    decision = output["decision"]
    print()
    print("=" * 70)
    print(f"  AGENT 1 IA — PLANIFICATION OF : {output['of_id']}")
    print("=" * 70)

    if output.get("ai_enhanced"):
        score = output.get("global_risk_score", "?")
        level = output.get("risk_level", "?")
        print(f"  🤖 Analyse IA activée — Score de risque : {score}/100 ({level})")
        if output.get("risk_factors"):
            print("  Facteurs de risque :")
            for rf in output["risk_factors"]:
                print(f"    • {rf.get('factor', '?')} : {rf.get('score', '?')}/100 — {rf.get('detail', '')}")
        if output.get("recommended_start_slot"):
            print(f"  📅 Créneau recommandé : {output['recommended_start_slot']}")
        if output.get("estimated_production_days"):
            print(f"  ⏱️  Durée estimée : {output['estimated_production_days']} jours")
        if output.get("sla_impact"):
            print(f"  📊 Impact SLA : {output['sla_impact']}")
        print()
    else:
        print("  ℹ️  Mode MVP (sans IA)")
        print()

    if decision == "FULL_RELEASE":
        print(f"  ✅ Décision : {decision}")
        print(f"  ➜  Nouveau statut OF : {output['new_status']}")
        print(f"  ➜  {output['instruction']}")
    elif decision == "PARTIAL_RELEASE":
        print(f"  ⚠️  Décision : {decision}")
        print(f"  ➜  Nouveau statut OF : {output['new_status']}")
        print()
        print("  Composants manquants :")
        for mc in output.get("missing_components", []):
            crit = " 🔴 CRITIQUE" if mc.get("isCritical") else ""
            print(f"    • {mc['itemCode']}{crit} — besoin {mc['qtyNeeded']}, "
                  f"dispo {mc['qtyAvailable']}, manque {mc['qtyShortage']}")
        if output.get("cutoff_operation"):
            co = output["cutoff_operation"]
            print(f"\n  Opération de coupure : {co['operationId']} (séq. {co['sequence']})")
        print(f"\n  📋 Consigne : {output['instruction']}")
    elif decision == "DELAYED_RELEASE":
        print(f"  🛑 Décision : {decision}")
        print(f"  ➜  Nouveau statut OF : {output['new_status']}")
        print()
        print("  Composants manquants :")
        for mc in output.get("missing_components", []):
            crit = " 🔴 CRITIQUE" if mc.get("isCritical") else ""
            print(f"    • {mc['itemCode']}{crit} — besoin {mc['qtyNeeded']}, "
                  f"dispo {mc['qtyAvailable']}, manque {mc['qtyShortage']}")
        print(f"\n  📋 Consigne : {output['instruction']}")

    if output.get("ai_reasoning"):
        print()
        print("  💬 Explication IA :")
        # Wrap long reasoning text
        reasoning = output["ai_reasoning"]
        for line in reasoning.split("\n"):
            print(f"     {line}")

    print("=" * 70)
    print()


# =============================================================================
# Point d'entrée (async)
# =============================================================================

async def async_main(data_dir: str, output_path: Optional[str]):
    print()
    print("🏭 Agent 1 IA — Planification intelligente OF")
    print("-" * 50)

    # ── Étape 1-3 : chargement des données ────────────────────────────────
    print("[1/9] Chargement de l'OF...")
    of = load_of(data_dir)
    print(f"   Statut actuel : {of.get('status', 'N/A')}")
    print(f"   Priorité : {of.get('priority', 'N/A')} — Échéance : {of.get('dueDate', 'N/A')}")

    print("[2/9] Chargement de la BOM et de la gamme...")
    components, operations = load_bom_and_routing(data_dir, of["productCode"])
    for comp in components:
        crit = " 🔴" if comp.get("isCritical") else ""
        print(f"   • {comp['itemCode']}{crit} — {comp['qtyPerUnit']}/u × {of['quantity']} = {comp['qtyPerUnit'] * of['quantity']}")

    print("[3/9] Chargement du stock...")
    stock = load_stock(data_dir)
    for code, qty in stock.items():
        print(f"   • {code} : {qty}")

    # ── Étape 4 : disponibilité ────────────────────────────────────────────
    print("[4/9] Vérification de la disponibilité...")
    missing_components = check_availability(components, of["quantity"], stock)
    for comp in components:
        qty_needed = comp["qtyPerUnit"] * of["quantity"]
        qty_avail = stock.get(comp["itemCode"], 0)
        icon = "✅" if qty_avail >= qty_needed else "❌"
        print(f"   {icon} {comp['itemCode']} : besoin {qty_needed}, dispo {qty_avail}")

    # ── Étape 5 : décision MVP ─────────────────────────────────────────────
    print("[5/9] Décision MVP (déterministe)...")
    mvp_decision = decide_mvp(missing_components)
    print(f"   Décision MVP : {mvp_decision}")

    # ── Étape 6 : coupure ──────────────────────────────────────────────────
    cutoff_op = None
    last_doable_op = None
    if mvp_decision == "PARTIAL_RELEASE":
        print("[6/9] Identification de l'opération de coupure...")
        cutoff_op = find_cutoff_operation(operations, missing_components)
        last_doable_op = find_last_doable_operation(operations, cutoff_op)
        if cutoff_op:
            print(f"   ➜ Coupure à : {cutoff_op['operationId']} (séq. {cutoff_op['sequence']})")
    else:
        print("[6/9] Pas de coupure (release complet)")

    # ── Étape 7 : chargement données IA optionnelles ──────────────────────
    print("[7/9] Chargement des données IA (optionnelles)...")
    historical_ofs = load_optional_json(data_dir, "historical_ofs.json")
    machine_calendar = load_optional_json(data_dir, "machine_calendar.json")
    sla_rules = load_optional_json(data_dir, "sla_rules.json")
    demand_forecast = load_optional_json(data_dir, "demand_forecast.json")

    # ── Étape 8 : analyse IA ──────────────────────────────────────────────
    ai_analysis = None
    decision = mvp_decision  # fallback

    project_endpoint = (
        os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        or os.getenv("AI_FOUNDRY_PROJECT_ENDPOINT")
    )
    deployment_name = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4.1")

    if project_endpoint:
        print("[8/9] 🤖 Appel à l'agent IA...")
        try:
            agent = OFPlanningAgent(project_endpoint, deployment_name)
            ai_analysis = await agent.analyze(
                of=of,
                components=components,
                operations=operations,
                stock=stock,
                missing_components=missing_components,
                mvp_decision=mvp_decision,
                cutoff_op=cutoff_op,
                last_doable_op=last_doable_op,
                historical_ofs=historical_ofs,
                machine_calendar=machine_calendar,
                sla_rules=sla_rules,
                demand_forecast=demand_forecast,
            )
            # L'IA peut changer la décision (ex : PARTIAL → DELAYED)
            ai_decision = ai_analysis.get("decision", mvp_decision)
            if ai_decision in ("FULL_RELEASE", "PARTIAL_RELEASE", "DELAYED_RELEASE"):
                decision = ai_decision
                print(f"   IA → décision : {decision}")
            else:
                print(f"   ⚠️  Décision IA invalide ({ai_decision}), on garde MVP : {mvp_decision}")
            print(f"   IA → risque : {ai_analysis.get('global_risk_score', '?')}/100 "
                  f"({ai_analysis.get('risk_level', '?')})")
        except Exception as e:
            print(f"   ⚠️  Erreur IA : {e}")
            print(f"   Fallback → décision MVP : {mvp_decision}")
    else:
        print("[8/9] ℹ️  Azure AI non configuré — mode MVP uniquement")

    # ── Étape 9 : output + persistance ─────────────────────────────────────
    output_file = output_path or os.path.join(data_dir, f"agent1_output_{of['id']}.json")

    print("[9/9] Construction output & persistance...")
    output = build_output(of, decision, missing_components, cutoff_op, last_doable_op, ai_analysis)
    persist_output(output, output_file)
    update_of_status(data_dir, of, output["new_status"])

    print_summary(output)


def main():
    parser = argparse.ArgumentParser(description="Agent 1 IA — Planification intelligente OF")
    parser.add_argument(
        "--data-dir",
        default=os.path.join(os.path.dirname(__file__), "..", "data"),
        help="Répertoire contenant les fichiers de données",
    )
    parser.add_argument("--output", default=None, help="Chemin du fichier output")
    args = parser.parse_args()
    data_dir = os.path.abspath(args.data_dir)
    asyncio.run(async_main(data_dir, args.output))


if __name__ == "__main__":
    main()
