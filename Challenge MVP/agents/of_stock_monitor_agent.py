#!/usr/bin/env python3
"""Agent 2 — Surveillance stock & reprise d'OF partiels.

Surveille les OF en statut PartiallyReleased. Dès que les pièces manquantes
sont en stock, passe l'OF en ReadyToResume et génère une consigne de reprise.

Usage:
    python agents/of_stock_monitor_agent.py [--data-dir DATA_DIR]

Par défaut lit les fichiers dans le dossier ``data/`` à la racine du projet.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

# =============================================================================
# Chargement des données (Étapes 1-3)
# =============================================================================

def load_json(filepath: str) -> Any:
    """Charge et parse un fichier JSON."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def load_orders_to_watch(data_dir: str) -> List[Dict]:
    """Étape 1 — Charger les OF à surveiller (statut PartiallyReleased)."""
    data = load_json(os.path.join(data_dir, "orders_partially_released.json"))
    orders = [o for o in data["orders"] if o["status"] == "PartiallyReleased"]
    print(f"   {len(orders)} OF en PartiallyReleased à surveiller")
    for o in orders:
        print(f"   • {o['of_id']} — produit {o.get('productCode', 'N/A')}")
    return orders


def load_agent1_output(data_dir: str, of_id: str, agent1_output_file: str | None = None) -> Dict:
    """Étape 2 — Charger l'output de l'Agent 1 pour un OF donné.

    Utilise en priorité le champ ``agent1_output_file`` de la liste des OF,
    sinon cherche ``agent1_output_<of_id>.json`` puis ``agent1_output.json``.
    """
    candidates = []
    if agent1_output_file:
        candidates.append(os.path.join(data_dir, agent1_output_file))
    candidates.append(os.path.join(data_dir, f"agent1_output_{of_id}.json"))
    candidates.append(os.path.join(data_dir, "agent1_output.json"))

    state = None
    for path in candidates:
        if os.path.exists(path):
            state = load_json(path)
            print(f"   Agent 1 output chargé depuis : {os.path.basename(path)}")
            break

    if state is None:
        raise FileNotFoundError(
            f"Aucun output Agent 1 trouvé pour {of_id} "
            f"(cherché : {', '.join(os.path.basename(p) for p in candidates)})"
        )

    # Vérification de cohérence
    if state.get("of_id") != of_id:
        raise ValueError(
            f"L'output Agent 1 concerne {state.get('of_id')} mais l'OF demandé est {of_id}"
        )

    print(f"   {len(state.get('missing_components', []))} composant(s) manquant(s) déclarés par Agent 1")
    for mc in state.get("missing_components", []):
        print(f"     ↳ {mc['itemCode']} — besoin {mc['qtyNeeded']}, "
              f"était dispo {mc.get('qtyAvailable', '?')}, manquait {mc.get('qtyShortage', '?')}")
    if state.get("resume_from_operation"):
        ro = state["resume_from_operation"]
        print(f"   Opération de reprise prévue : {ro.get('operationId', '?')} (séq. {ro.get('sequence', '?')})")
    return state


def load_stock(data_dir: str) -> Dict[str, int]:
    """Étape 3 — Charger le snapshot de stock actuel."""
    snapshot = load_json(os.path.join(data_dir, "stock_snapshot.json"))
    stock = {item["itemCode"]: item["qtyAvailable"] for item in snapshot["items"]}
    print(f"   Stock chargé : {len(stock)} références (snapshot {snapshot['timestamp']})")
    return stock


# =============================================================================
# Logique métier (Étapes 4-5)
# =============================================================================

def check_shortages_resolved(
    missing_components: List[Dict], stock: Dict[str, int]
) -> Tuple[List[Dict], List[Dict]]:
    """Étape 4 — Vérifier si les pénuries sont résolues.

    Retourne (resolved, still_missing).
    """
    resolved: List[Dict] = []
    still_missing: List[Dict] = []

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
            })

    return resolved, still_missing


def decide_new_status(still_missing: List[Dict]) -> str:
    """Étape 5 — Décision : ReadyToResume ou PartiallyReleased."""
    return "ReadyToResume" if len(still_missing) == 0 else "PartiallyReleased"


# =============================================================================
# Construction et persistance de l'output (Étapes 6-7)
# =============================================================================

def build_output(
    of_id: str,
    previous_status: str,
    new_status: str,
    agent1_state: Dict,
    resolved: List[Dict],
    still_missing: List[Dict],
) -> Dict:
    """Étape 6 — Construire l'output structuré de l'Agent 2."""

    output: Dict[str, Any] = {
        "of_id": of_id,
        "previous_status": previous_status,
        "new_status": new_status,
        "resolved_components": resolved,
        "still_missing_components": still_missing,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if new_status == "ReadyToResume":
        resume_op = agent1_state.get("resume_from_operation", {})
        output["resume_from_operation"] = resume_op

        parts_list = ", ".join(
            f"{r['itemCode']} ({r['qtyNeeded']}/{r['qtyAvailableNow']})"
            for r in resolved
        )
        op_id = resume_op.get("operationId", "?")
        output["instruction"] = (
            f"Reprendre la production à partir de l'opération {op_id}. "
            f"Les composants manquants sont maintenant disponibles : {parts_list}."
        )
    else:
        shortage_detail = ", ".join(
            f"{sm['itemCode']} (manque {sm['qtyStillShort']})"
            for sm in still_missing
        )
        output["instruction"] = (
            f"OF toujours en attente — composants insuffisants : {shortage_detail}."
        )

    return output


def persist_output(output: Dict, output_path: str) -> None:
    """Étape 7a — Écrire le résultat dans un fichier JSON."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"   Output écrit dans : {output_path}")


def update_of_status(data_dir: str, of_id: str, new_status: str) -> None:
    """Étape 7c — Mettre à jour le statut de l'OF dans of.json (si applicable)."""
    of_path = os.path.join(data_dir, "of.json")
    if not os.path.exists(of_path):
        print(f"   ⚠️  of.json introuvable, mise à jour OF ignorée")
        return
    of = load_json(of_path)
    if of.get("id") == of_id:
        of["status"] = new_status
        with open(of_path, "w", encoding="utf-8") as f:
            json.dump(of, f, indent=2, ensure_ascii=False)
        print(f"   OF mis à jour : status → {new_status} (dans of.json)")
    else:
        print(f"   ℹ️  of.json concerne {of.get('id')}, pas {of_id} — mise à jour ignorée")


def notify(output: Dict) -> None:
    """Étape 7b — Notification atelier / superviseur (simulée en console)."""
    ts = output["timestamp"]
    of_id = output["of_id"]
    new_status = output["new_status"]

    print()
    if new_status == "ReadyToResume":
        resume_op = output.get("resume_from_operation", {})
        op_id = resume_op.get("operationId", "?")
        op_desc = resume_op.get("description", "")
        parts = ", ".join(
            f"{r['itemCode']} ({r['qtyNeeded']}/{r['qtyAvailableNow']})"
            for r in output["resolved_components"]
        )
        print(f"   📢 NOTIFICATION [{ts}]")
        print(f"   OF {of_id} prêt à reprendre.")
        print(f"   ➜ Reprendre à partir de l'opération {op_id}" + (f" ({op_desc})" if op_desc else "") + ".")
        print(f"   ➜ Composants disponibles : {parts}.")
    else:
        shortage = ", ".join(
            f"{sm['itemCode']} (manque {sm['qtyStillShort']})"
            for sm in output["still_missing_components"]
        )
        print(f"   ℹ️  NOTIFICATION [{ts}]")
        print(f"   OF {of_id} toujours en attente.")
        print(f"   ➜ Composants manquants : {shortage}.")


# =============================================================================
# Affichage console
# =============================================================================

def print_summary(results: List[Dict]) -> None:
    """Affiche un résumé global de tous les OF traités."""
    ready = [r for r in results if r["new_status"] == "ReadyToResume"]
    waiting = [r for r in results if r["new_status"] == "PartiallyReleased"]

    print()
    print("=" * 65)
    print("  AGENT 2 — SURVEILLANCE STOCK & REPRISE")
    print("=" * 65)
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
            print(f"    • {r['of_id']} → {parts}")

    print("=" * 65)
    print()


# =============================================================================
# Point d'entrée
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Agent 2 — Surveillance stock & reprise OF")
    parser.add_argument(
        "--data-dir",
        default=os.path.join(os.path.dirname(__file__), "..", "data"),
        help="Répertoire contenant les fichiers d'input/output",
    )
    args = parser.parse_args()

    data_dir = os.path.abspath(args.data_dir)

    print()
    print("🔍 Agent 2 — Surveillance stock & reprise OF")
    print("-" * 50)

    # Étape 1 — Charger les OF à surveiller
    print("[1/7] Chargement des OF en PartiallyReleased...")
    orders = load_orders_to_watch(data_dir)

    if not orders:
        print("   Aucun OF à surveiller. Fin.")
        return

    # Étape 3 — Charger le stock (une seule fois pour tous les OF)
    print("[3/7] Chargement du stock actuel...")
    stock = load_stock(data_dir)
    for item_code, qty in stock.items():
        print(f"   • {item_code} : {qty} en stock")

    results: List[Dict] = []

    for order in orders:
        of_id = order["of_id"]
        print()
        print(f"  ┌── Traitement OF : {of_id}")
        print(f"  │")

        # Étape 2 — Charger l'output Agent 1 (utilise agent1_output_file si disponible)
        print(f"  │ [2/7] Chargement output Agent 1...")
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

        # Étape 4 — Vérifier si les pénuries sont résolues
        print(f"  │ [4/7] Vérification des pénuries...")
        resolved, still_missing = check_shortages_resolved(missing_components, stock)

        if resolved:
            for r in resolved:
                print(f"  │   ✅ {r['itemCode']} — dispo {r['qtyAvailableNow']} ≥ besoin {r['qtyNeeded']}")
        if still_missing:
            for sm in still_missing:
                print(f"  │   ❌ {sm['itemCode']} — dispo {sm['qtyAvailableNow']} < besoin {sm['qtyNeeded']} (manque {sm['qtyStillShort']})")

        # Étape 5 — Décision
        print(f"  │ [5/7] Prise de décision...")
        new_status = decide_new_status(still_missing)
        print(f"  │   Décision : {new_status}")

        # Étape 6 — Construire l'output
        print(f"  │ [6/7] Construction de l'output...")
        output = build_output(
            of_id=of_id,
            previous_status=order["status"],
            new_status=new_status,
            agent1_state=agent1_state,
            resolved=resolved,
            still_missing=still_missing,
        )

        # Étape 7 — Persister + notifier + mise à jour OF
        print(f"  │ [7/7] Persistance, notification & mise à jour OF...")
        output_path = os.path.join(data_dir, f"agent2_output_{of_id}.json")
        persist_output(output, output_path)
        if new_status == "ReadyToResume":
            update_of_status(data_dir, of_id, new_status)
        notify(output)

        results.append(output)
        print(f"  └── OF {of_id} traité")

    # Résumé global
    print_summary(results)


if __name__ == "__main__":
    main()
