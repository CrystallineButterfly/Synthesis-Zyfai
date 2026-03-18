"""Project-specific context for YieldMind Engine."""

        from __future__ import annotations

        PROJECT_CONTEXT = {
    "project_name": "YieldMind Engine",
    "track": "Zyfai",
    "pitch": "A yield-aware operator that measures available yield, budgets compute spend, and prepares payout plans for AI workloads.",
    "overlap_targets": [
        "Bankr Gateway",
        "PayWithLocus",
        "Venice Private Agents",
        "ERC-8004 Receipts",
        "Uniswap Agentic Finance",
        "Lido stETH Treasury"
    ],
    "goals": [
        "discover a bounded opportunity",
        "plan a dry-run-first action",
        "verify receipts and proofs"
    ]
}


        def seed_targets() -> list[str]:
            """Return the first batch of overlap targets for planning."""
            return list(PROJECT_CONTEXT['overlap_targets'])
