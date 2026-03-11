"""Quick E2E test of data flow."""
from data import (
    get_stock_updates_preview, resume_of, run_agent2,
    build_seed_orders, run_agent1, run_orchestrator,
)

orders = build_seed_orders()
print("OK - all imports work")

# Agent 1 on "Moyen" (of-2026-00201)
OF = "of-2026-00201"
o1 = run_agent1(OF, orders)
print(f"Agent1: {o1['decision']} | status={orders[OF]['status']}")

# Orchestrator
wl = run_orchestrator({OF: o1})
print(f"Watchlist: {len(wl)} items")

# Stock preview
sp = get_stock_updates_preview(orders, wl)
for p in sp:
    print(f"  Stock preview {p['orderNumber']}: has_arrivals={p['has_arrivals']}, arrivals={p['arrivals']}")

# Agent 2
r2 = run_agent2(orders, {OF: o1}, wl)
print(f"Agent2: status={r2[0]['new_status']}, arrivals={r2[0]['stock_arrivals']}")

# Resume
resume_of(OF, orders)
print(f"After resume: status={orders[OF]['status']}")

print("\n=== ALL OK ===")
