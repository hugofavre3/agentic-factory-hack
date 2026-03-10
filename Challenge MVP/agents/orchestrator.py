#!/usr/bin/env python3
"""Orchestrateur — Communication inter-agents.

Lit tous les fichiers agent1_output_*.json dans le dossier data/,
filtre ceux en statut PartiallyReleased, et génère le fichier
orders_partially_released.json consommé par l'Agent 2.

Usage:
    python agents/orchestrator.py [--data-dir DATA_DIR]
"""

import argparse
import glob
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List


def load_json(filepath: str) -> Any:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def scan_agent1_outputs(data_dir: str) -> List[Dict]:
    """Scanne tous les fichiers agent1_output_*.json et retourne les entrées."""
    pattern = os.path.join(data_dir, "agent1_output_*.json")
    files = sorted(glob.glob(pattern))
    entries: List[Dict] = []

    print(f"   Scan : {pattern}")
    print(f"   {len(files)} fichier(s) agent1_output_*.json trouvé(s)")

    for filepath in files:
        filename = os.path.basename(filepath)
        try:
            data = load_json(filepath)
            entry = {
                "of_id": data.get("of_id", ""),
                "status": data.get("new_status", ""),
                "productCode": data.get("productCode", ""),
                "decision": data.get("decision", ""),
                "agent1_output_file": filename,
            }
            entries.append(entry)
            print(f"   • {filename} → OF {entry['of_id']} — statut {entry['status']} ({entry['decision']})")
        except Exception as e:
            print(f"   ⚠️  Erreur lecture {filename} : {e}")

    return entries


def build_orders_partially_released(entries: List[Dict]) -> Dict:
    """Filtre les entrées PartiallyReleased/Delayed et construit la liste pour Agent 2."""
    # L'Agent 1 IA peut produire le statut "Delayed" en plus de "PartiallyReleased"
    watchable = [e for e in entries if e["status"] in ("PartiallyReleased", "Delayed")]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_agent1_outputs": len(entries),
        "partially_released_count": len(watchable),
        "orders": [
            {
                "of_id": e["of_id"],
                "status": e["status"],
                "productCode": e["productCode"],
                "agent1_output_file": e["agent1_output_file"],
            }
            for e in watchable
        ],
    }


def main():
    parser = argparse.ArgumentParser(
        description="Orchestrateur — Génère orders_partially_released.json à partir des outputs Agent 1"
    )
    parser.add_argument(
        "--data-dir",
        default=os.path.join(os.path.dirname(__file__), "..", "data"),
        help="Répertoire contenant les fichiers agent1_output_*.json",
    )
    args = parser.parse_args()
    data_dir = os.path.abspath(args.data_dir)

    print()
    print("🔗 Orchestrateur — Communication inter-agents")
    print("-" * 50)

    # Scanner les outputs Agent 1
    print("[1/2] Scan des outputs Agent 1...")
    entries = scan_agent1_outputs(data_dir)

    if not entries:
        print("   Aucun output Agent 1 trouvé. Fin.")
        return

    # Construire et écrire orders_partially_released.json
    print("[2/2] Génération de orders_partially_released.json...")
    result = build_orders_partially_released(entries)

    output_path = os.path.join(data_dir, "orders_partially_released.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"   Fichier écrit : {output_path}")
    print()
    print("=" * 55)
    print(f"  Total outputs Agent 1     : {result['total_agent1_outputs']}")
    print(f"  OF en Released            : {result['total_agent1_outputs'] - result['partially_released_count']}")
    print(f"  OF en PartiallyReleased   : {result['partially_released_count']}")
    print("=" * 55)

    if result["partially_released_count"] > 0:
        print()
        print("  OF à surveiller par Agent 2 :")
        for o in result["orders"]:
            print(f"    • {o['of_id']} — source : {o['agent1_output_file']}")
    else:
        print("  Aucun OF à surveiller — tous les OF sont Released.")

    print()


if __name__ == "__main__":
    main()
