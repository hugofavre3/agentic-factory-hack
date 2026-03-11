# Agents OF IA - methodologie synthétique

Ce document verifie les etapes de vos deux agents OF IA a partir de l'implementation presente dans le repo, puis ajoute la brique orchestrator et des exemples d'inputs/outputs.

## Vue d'ensemble

Chaine actuelle:

1. Agent 1 lit l'OF, la BOM, la gamme, le stock, puis enrichit la decision avec l'IA.
2. L'orchestrateur collecte les outputs Agent 1 et prepare la liste des OF a surveiller.
3. Agent 2 lit cette liste, recontrole le stock, recommande les achats et decide la reprise.

Point de vigilance sur le vocabulaire:

1. Dans le code, `NE_PAS_DEMARRER` est implemente sous la forme `DELAYED_RELEASE`.
2. Le statut OF ecrit par Agent 1 n'est pas `FULL_RELEASE` ou `PARTIAL_RELEASE`, mais `Released`, `PartiallyReleased` ou `Delayed`.

## Validation rapide par rapport au code

### Agent 1 - OF planning IA

| Bloc | Methodologie tres synthetique | Etat dans le repo |
|---|---|---|
| Lire OF + gamme + BOM + stock | Charger et normaliser `of.json`, `bom.json`, `routing.json`, `stock_snapshot.json` | OK |
| Calcul besoins vs stock | Multiplier `qtyPerUnit * quantity`, comparer au stock, isoler les manquants | OK |
| Detecter pieces critiques | Marquer les lignes BOM `isCritical=true` et les garder dans les manquants | OK |
| Trouver l'operation de coupure | Parcourir la gamme dans l'ordre et prendre la premiere operation qui consomme une piece manquante | OK |
| Estimer risque via historique | Donner a l'IA les OF similaires, retards, blocages et impact SLA pour scorer le risque | OK |
| Analyser le calendrier ressources | Donner a l'IA les slots machine disponibles, charge, indisponibilites, puis recommander un slot de depart | OK |
| Decider FULL / PARTIAL / NE PAS DEMARRER | Appliquer une politique hybride: base deterministe + arbitrage IA entre `FULL_RELEASE`, `PARTIAL_RELEASE`, `DELAYED_RELEASE` | OK avec renommage |
| Generer une reco IA de timing | Produire `recommended_start_slot`, `global_risk_score`, `risk_level`, `ai_reasoning` | OK |
| Mettre a jour l'OF + output Agent 2 | Ecrire `new_status` dans `of.json` et produire `agent1_output_*.json` | OK |

Methodologie bloc par bloc:

1. Bloc data: charger les sources, verifier la coherence `productCode`, trier la gamme par sequence.
2. Bloc shortage: calculer besoin theorique par composant, puis isoler manque, criticite et quantite manquante.
3. Bloc cutoff: identifier la premiere operation bloquee, puis la derniere operation encore executable avant blocage.
4. Bloc risk: exposer a l'IA l'historique d'OF comparables, les retards passes, les composants critiques et les regles SLA.
5. Bloc planning: exposer a l'IA les slots disponibles et laisser le modele choisir le meilleur compromis charge/date/risque.
6. Bloc decision: partir de la decision MVP, puis laisser l'IA confirmer ou durcir la decision en `DELAYED_RELEASE` si le risque est trop fort.
7. Bloc persistence: ecrire le statut OF, la consigne atelier, l'operation de reprise et l'output JSON pour la suite.

### Agent 2 - OF stock monitor IA

| Bloc | Methodologie tres synthetique | Etat dans le repo |
|---|---|---|
| Lire OF PartiallyReleased + output Agent 1 | Consommer `orders_partially_released.json` puis recharger le detail via `agent1_output_*.json` | OK |
| Surveiller la disponibilite des manquants | Rejouer la comparaison entre les manquants Agent 1 et le `stock_snapshot.json` courant | OK |
| Estimer ETA + risque tant que piece indisponible | Donner a l'IA fournisseurs, historique de commandes, forecast et SLA pour predire ETA et risque | OK |
| Optimiser la selection fournisseur | Scoring IA guide par fiabilite 40%, delai 35%, cout 25% | OK |
| Arbitrer entre OF concurrents | Produire une `resume_priority` par OF, mais pas de moteur global d'allocation partagee | Partiel |
| Passer l'OF en ReadyToResume | Si tous les manquants sont resolus, ecrire `ReadyToResume` et la consigne de reprise | OK |
| Notifier atelier / superviseur | Generer `instruction` et, si IA active, `ai_notification` | OK |
| Ecrire output JSON de decision | Produire `agent2_output_*.json` avec composants resolus, manquants, priorite et ETA | OK |

Methodologie bloc par bloc:

1. Bloc watchlist: lire la liste des OF surveilles produite par l'orchestrateur.
2. Bloc stock check: pour chaque OF, reevaluer les pieces manquantes avec le stock courant.
3. Bloc procurement IA: si le manque persiste, demander a l'IA le meilleur fournisseur, la quantite, l'ETA et le risque global.
4. Bloc resume policy: si plus aucun manque, basculer en `ReadyToResume`; sinon garder l'OF en attente.
5. Bloc prioritisation: utiliser `resume_priority` comme score de reprise, en notant qu'il n'y a pas encore d'arbitrage multi-OF centralise.
6. Bloc notification: produire un message court, exploitable atelier, avec la prochaine action.
7. Bloc persistence: mettre a jour l'OF et serialiser la decision dans un output JSON.

### Orchestrator

| Bloc | Methodologie tres synthetique | Etat dans le repo |
|---|---|---|
| Scanner les outputs Agent 1 | Chercher tous les `agent1_output_*.json` dans `data/` | OK |
| Filtrer les OF a surveiller | Ne garder que `PartiallyReleased` et `Delayed` | OK |
| Construire la watchlist Agent 2 | Generer `orders_partially_released.json` avec `of_id`, statut, produit et fichier source | OK |
| Jouer le role de passerelle inter-agents | Standardiser le handoff Agent 1 -> Agent 2 | OK |

Methodologie:

1. L'orchestrateur ne prend pas de decision metier.
2. Il consolide les outputs Agent 1.
3. Il transforme ces outputs en file d'attente exploitable par Agent 2.
4. Il garantit un contrat d'echange stable entre les deux agents.

## Inputs et outputs attendus

### Agent 1 - inputs

Exemple minimal d'input OF:

```json
{
  "id": "of-2026-00123",
  "orderNumber": "OF-2026-00123",
  "productCode": "BOGIE_Y32",
  "quantity": 4,
  "priority": "High",
  "status": "Created",
  "dueDate": "2026-03-25T00:00:00Z"
}
```

Exemple minimal d'input BOM:

```json
{
  "productCode": "BOGIE_Y32",
  "components": [
    {
      "itemCode": "BRAKE_DISC",
      "qtyPerUnit": 4,
      "isCritical": true
    }
  ]
}
```

Exemple minimal d'input gamme:

```json
{
  "productCode": "BOGIE_Y32",
  "operations": [
    {
      "operationId": "OP30_SUSPENSION",
      "sequence": 30,
      "requiredComponents": []
    },
    {
      "operationId": "OP40_BRAKE_ASSEMBLY",
      "sequence": 40,
      "requiredComponents": ["BRAKE_DISC"]
    }
  ]
}
```

Exemple minimal d'input stock:

```json
{
  "items": [
    {
      "itemCode": "BRAKE_DISC",
      "qtyAvailable": 0
    }
  ]
}
```

### Agent 1 - output

Exemple reel simplifie:

```json
{
  "of_id": "of-2026-00123",
  "decision": "PARTIAL_RELEASE",
  "new_status": "PartiallyReleased",
  "global_risk_score": 62,
  "risk_level": "MEDIUM",
  "recommended_start_slot": "SLOT-2026-03-11-AM",
  "missing_components": [
    {
      "itemCode": "BRAKE_DISC",
      "qtyNeeded": 16,
      "qtyAvailable": 0,
      "qtyShortage": 16,
      "isCritical": true
    }
  ],
  "cutoff_operation": {
    "operationId": "OP40_BRAKE_ASSEMBLY",
    "sequence": 40
  },
  "resume_from_operation": {
    "operationId": "OP40_BRAKE_ASSEMBLY",
    "sequence": 40
  },
  "instruction": "Produire jusqu'a OP30_SUSPENSION inclus, puis attendre BRAKE_DISC"
}
```

### Orchestrator - input/output

Input: un ou plusieurs `agent1_output_*.json` dans `data/`.

Output genere pour Agent 2:

```json
{
  "generated_at": "2026-03-10T17:25:13.556979+00:00",
  "total_agent1_outputs": 1,
  "partially_released_count": 1,
  "orders": [
    {
      "of_id": "of-2026-00123",
      "status": "PartiallyReleased",
      "productCode": "BOGIE_Y32",
      "agent1_output_file": "agent1_output_of-2026-00123.json"
    }
  ]
}
```

### Agent 2 - inputs

Input principal:

```json
{
  "of_id": "of-2026-00123",
  "status": "PartiallyReleased",
  "productCode": "BOGIE_Y32",
  "agent1_output_file": "agent1_output_of-2026-00123.json"
}
```

Input detaille recharge depuis Agent 1:

```json
{
  "of_id": "of-2026-00123",
  "decision": "PARTIAL_RELEASE",
  "new_status": "PartiallyReleased",
  "missing_components": [
    {
      "itemCode": "BRAKE_DISC",
      "qtyNeeded": 16,
      "isCritical": true
    }
  ],
  "resume_from_operation": {
    "operationId": "OP40_BRAKE_ASSEMBLY",
    "sequence": 40
  }
}
```

### Agent 2 - output

Cas 1 - pieces de retour en stock, OF reprenable:

```json
{
  "of_id": "of-2026-00123",
  "previous_status": "PartiallyReleased",
  "new_status": "ReadyToResume",
  "resolved_components": [
    {
      "itemCode": "BRAKE_DISC",
      "qtyNeeded": 16,
      "qtyAvailableNow": 20
    }
  ],
  "still_missing_components": [],
  "resume_from_operation": {
    "operationId": "OP40_BRAKE_ASSEMBLY",
    "sequence": 40
  },
  "instruction": "Reprendre la production a partir de l'operation OP40_BRAKE_ASSEMBLY"
}
```

Cas 2 - pieces toujours manquantes, OF toujours en attente:

```json
{
  "of_id": "of-2026-00123",
  "previous_status": "PartiallyReleased",
  "new_status": "PartiallyReleased",
  "resolved_components": [],
  "still_missing_components": [
    {
      "itemCode": "BRAKE_DISC",
      "qtyNeeded": 16,
      "qtyAvailableNow": 4,
      "qtyStillShort": 12,
      "isCritical": true
    }
  ],
  "resume_priority": 1,
  "supplier_recommendations": [
    {
      "itemCode": "BRAKE_DISC",
      "recommended_supplier": "SUP-001",
      "supplier_name": "BrakeSystems Europe",
      "supplier_score": 87,
      "order_qty": 12,
      "predicted_eta": "2026-03-14",
      "confidence": 0.82
    }
  ],
  "overall_eta_days": 3,
  "risk_assessment": "Retard probable si non acceleration fournisseur"
}
```

## Recommandation d'architecture

Pour vos slides ou votre soutenance, vous pouvez presenter la chaine ainsi:

1. Agent 1 = decision de lancement partiel basee sur stock, risque et planning.
2. Orchestrator = passerelle de handoff entre decision de lancement et surveillance.
3. Agent 2 = surveillance continue, optimisation fournisseur et decision de reprise.

## Limites actuelles a mentionner honnetement

1. L'arbitrage entre OF concurrents existe au niveau du score `resume_priority`, mais pas encore comme moteur global d'allocation de stock partage.
2. La decision de non-demarrage est nommee `DELAYED_RELEASE` dans le code.
3. L'orchestrateur consolide les fichiers, mais n'ordonnance pas lui-meme les traitements.
