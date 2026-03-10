#!/usr/bin/env python3
"""Agent 1 — Planification partielle d'Ordre de Fabrication (OF).

Lit un OF, vérifie la disponibilité des composants via BOM + stock,
et décide entre FULL_RELEASE ou PARTIAL_RELEASE.
En cas de release partiel, identifie l'opération de coupure dans la gamme.

Usage:
    python agents/of_planning_agent.py [--of DATA_DIR/of.json]

Par défaut lit les fichiers dans le dossier ``data/`` à la racine du projet.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# =============================================================================
# Chargement des données (Étapes 1-3)
# =============================================================================

def load_json(filepath: str) -> Any:
    """Charge et parse un fichier JSON."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def load_of(data_dir: str) -> Dict:
    """Étape 1 — Charger l'Ordre de Fabrication."""
    of = load_json(os.path.join(data_dir, "of.json"))
    print(f"   OF chargé : {of['id']} — produit {of['productCode']} × {of['quantity']}")
    return of


def load_bom_and_routing(data_dir: str, product_code: str):
    """Étape 2 — Charger la BOM et la gamme.

    Retourne (components, operations) où chaque composant est enrichi
    avec qtyNeeded = qtyPerUnit × quantité OF.
    """
    bom = load_json(os.path.join(data_dir, "bom.json"))
    routing = load_json(os.path.join(data_dir, "routing.json"))

    if bom["productCode"] != product_code:
        raise ValueError(
            f"BOM productCode ({bom['productCode']}) ne correspond pas à l'OF ({product_code})"
        )
    if routing["productCode"] != product_code:
        raise ValueError(
            f"Routing productCode ({routing['productCode']}) ne correspond pas à l'OF ({product_code})"
        )

    components = bom["components"]
    operations = sorted(routing["operations"], key=lambda op: op["sequence"])

    print(f"   BOM chargée : {len(components)} composants")
    print(f"   Gamme chargée : {len(operations)} opérations")
    return components, operations


def load_stock(data_dir: str) -> Dict[str, int]:
    """Étape 3 — Charger le snapshot de stock."""
    snapshot = load_json(os.path.join(data_dir, "stock_snapshot.json"))
    stock = {item["itemCode"]: item["qtyAvailable"] for item in snapshot["items"]}
    print(f"   Stock chargé : {len(stock)} références (snapshot {snapshot['timestamp']})")
    return stock


# =============================================================================
# Logique métier (Étapes 4-6)
# =============================================================================

def check_availability(components: List[Dict], of_qty: int, stock: Dict[str, int]) -> List[Dict]:
    """Étape 4 — Vérifier la disponibilité des composants.

    Retourne la liste des composants manquants (vide si tout est dispo).
    """
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
            })
    return missing


def decide(missing_components: List[Dict]) -> str:
    """Étape 5 — Décision : FULL_RELEASE ou PARTIAL_RELEASE."""
    return "FULL_RELEASE" if len(missing_components) == 0 else "PARTIAL_RELEASE"


def find_cutoff_operation(operations: List[Dict], missing_components: List[Dict]) -> Dict | None:
    """Étape 6 — Identifier l'opération de coupure.

    Parcourt les opérations en séquence et retourne la première qui
    consomme un composant manquant.
    """
    missing_codes = {mc["itemCode"] for mc in missing_components}

    for op in operations:
        required = set(op.get("requiredComponents", []))
        if required & missing_codes:  # intersection non vide → bloqué
            return op

    # Aucune opération ne référence les pièces manquantes (données incohérentes)
    return None


def find_last_doable_operation(operations: List[Dict], cutoff_op: Dict | None) -> Dict | None:
    """Trouve la dernière opération réalisable avant la coupure."""
    if cutoff_op is None:
        return None

    cutoff_seq = cutoff_op["sequence"]
    doable = [op for op in operations if op["sequence"] < cutoff_seq]
    return doable[-1] if doable else None


# =============================================================================
# Construction et persistance de l'output (Étapes 7-8)
# =============================================================================

def build_output(
    of: Dict,
    decision: str,
    missing_components: List[Dict],
    cutoff_op: Dict | None,
    last_doable_op: Dict | None,
) -> Dict:
    """Étape 7 — Construire l'objet output structuré."""

    output: Dict[str, Any] = {
        "of_id": of["id"],
        "orderNumber": of["orderNumber"],
        "productCode": of["productCode"],
        "quantity": of["quantity"],
        "decision": decision,
        "previous_status": of.get("status", "Created"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if decision == "FULL_RELEASE":
        output["new_status"] = "Released"
        output["missing_components"] = []
        output["instruction"] = "Production normale — tous les composants sont disponibles."
    else:
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

            # Construire la consigne humaine
            shortage_parts = ", ".join(
                f"{mc['itemCode']} (manque {mc['qtyShortage']})" for mc in missing_components
            )
            output["instruction"] = (
                f"Produire jusqu'à {last_doable_op['operationId']} (séq. {last_doable_op['sequence']}) inclus, "
                f"puis mettre de côté en attente de : {shortage_parts}"
            )
        else:
            # Toutes les opérations sont bloquées dès le début
            output["cutoff_operation"] = None
            output["resume_from_operation"] = None
            output["instruction"] = (
                "Aucune opération réalisable — tous les composants critiques manquent dès la première opération."
            )

    return output


def persist_output(output: Dict, output_path: str) -> None:
    """Étape 8a — Écrire le résultat dans un fichier JSON."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"   Output écrit dans : {output_path}")


def update_of_status(data_dir: str, of: Dict, new_status: str) -> None:
    """Étape 8b — Mettre à jour le statut de l'OF dans of.json."""
    of_path = os.path.join(data_dir, "of.json")
    of["status"] = new_status
    with open(of_path, "w", encoding="utf-8") as f:
        json.dump(of, f, indent=2, ensure_ascii=False)
    print(f"   OF mis à jour : status → {new_status} (dans of.json)")


# =============================================================================
# Affichage console
# =============================================================================

def print_summary(output: Dict) -> None:
    """Affiche un résumé lisible de la décision."""
    decision = output["decision"]

    print()
    print("=" * 65)
    print(f"  AGENT 1 — PLANIFICATION OF : {output['of_id']}")
    print("=" * 65)

    if decision == "FULL_RELEASE":
        print(f"  ✅ Décision : {decision}")
        print(f"  ➜  Nouveau statut OF : {output['new_status']}")
        print(f"  ➜  {output['instruction']}")
    else:
        print(f"  ⚠️  Décision : {decision}")
        print(f"  ➜  Nouveau statut OF : {output['new_status']}")
        print()
        print("  Composants manquants :")
        for mc in output["missing_components"]:
            print(
                f"    • {mc['itemCode']} — besoin {mc['qtyNeeded']}, "
                f"dispo {mc['qtyAvailable']}, manque {mc['qtyShortage']}"
            )
        if output.get("cutoff_operation"):
            co = output["cutoff_operation"]
            print()
            print(f"  Opération de coupure : {co['operationId']} (séq. {co['sequence']}) — {co['description']}")
        print()
        print(f"  📋 Consigne : {output['instruction']}")

    print("=" * 65)
    print()


# =============================================================================
# Point d'entrée
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Agent 1 — Planification partielle OF")
    parser.add_argument(
        "--data-dir",
        default=os.path.join(os.path.dirname(__file__), "..", "data"),
        help="Répertoire contenant of.json, bom.json, routing.json, stock_snapshot.json",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Chemin du fichier output (défaut : data/agent1_output_<of_id>.json)",
    )
    args = parser.parse_args()

    data_dir = os.path.abspath(args.data_dir)

    print()
    print("🏭 Agent 1 — Planification partielle OF")
    print("-" * 45)

    # Étape 1 — Charger l'OF
    print("[1/8] Chargement de l'OF...")
    of = load_of(data_dir)
    print(f"   Statut actuel : {of.get('status', 'N/A')}")
    print(f"   Priorité : {of.get('priority', 'N/A')} — Échéance : {of.get('dueDate', 'N/A')}")

    # Étape 2 — Charger BOM + gamme
    print("[2/8] Chargement de la BOM et de la gamme...")
    components, operations = load_bom_and_routing(data_dir, of["productCode"])
    for comp in components:
        print(f"   • BOM : {comp['itemCode']} — {comp.get('description','')} — {comp['qtyPerUnit']}/unité × {of['quantity']} = {comp['qtyPerUnit'] * of['quantity']} nécessaires")
    for op in operations:
        req = op.get('requiredComponents', [])
        print(f"   • Gamme : séq. {op['sequence']} — {op['operationId']} — composants requis : {req if req else '(aucun)'}")

    # Étape 3 — Charger le stock
    print("[3/8] Chargement du stock...")
    stock = load_stock(data_dir)
    for item_code, qty in stock.items():
        print(f"   • {item_code} : {qty} en stock")

    # Étape 4 — Vérifier la disponibilité
    print("[4/8] Vérification de la disponibilité des composants...")
    missing_components = check_availability(components, of["quantity"], stock)
    for comp in components:
        qty_needed = comp["qtyPerUnit"] * of["quantity"]
        qty_avail = stock.get(comp["itemCode"], 0)
        status_icon = "✅" if qty_avail >= qty_needed else "❌"
        print(f"   {status_icon} {comp['itemCode']} : besoin {qty_needed}, dispo {qty_avail}")
    if missing_components:
        print(f"   ⚠️  {len(missing_components)} composant(s) manquant(s)")
    else:
        print("   ✅ Tous les composants sont disponibles")

    # Étape 5 — Décision
    print("[5/8] Prise de décision...")
    decision = decide(missing_components)
    print(f"   Décision : {decision}")

    # Étape 6 — Opération de coupure (si partiel)
    cutoff_op = None
    last_doable_op = None
    if decision == "PARTIAL_RELEASE":
        print("[6/8] Identification de l'opération de coupure...")
        missing_codes = {mc["itemCode"] for mc in missing_components}
        for op in operations:
            req = set(op.get("requiredComponents", []))
            blocked = req & missing_codes
            if blocked:
                print(f"   🔴 séq. {op['sequence']} {op['operationId']} — BLOQUÉ par {blocked}")
            else:
                print(f"   🟢 séq. {op['sequence']} {op['operationId']} — OK")
        cutoff_op = find_cutoff_operation(operations, missing_components)
        last_doable_op = find_last_doable_operation(operations, cutoff_op)
        if cutoff_op:
            print(f"   ➜ Coupure à : {cutoff_op['operationId']} (séq. {cutoff_op['sequence']})")
            if last_doable_op:
                print(f"   ➜ Dernière opération réalisable : {last_doable_op['operationId']} (séq. {last_doable_op['sequence']})")
        else:
            print("   ⚠️  Aucune opération de coupure identifiée (vérifier le mapping requiredComponents)")
    else:
        print("[6/8] Pas de coupure nécessaire (release complet)")

    # Déterminer le chemin output (utilise of_id pour le nommage)
    output_path = args.output or os.path.join(data_dir, f"agent1_output_{of['id']}.json")

    # Étape 7 — Construction output
    print("[7/8] Construction de l'output...")
    output = build_output(of, decision, missing_components, cutoff_op, last_doable_op)

    # Étape 8 — Persistance + mise à jour OF
    print("[8/8] Persistance de l'output et mise à jour OF...")
    persist_output(output, output_path)
    update_of_status(data_dir, of, output["new_status"])

    # Résumé
    print_summary(output)


if __name__ == "__main__":
    main()
