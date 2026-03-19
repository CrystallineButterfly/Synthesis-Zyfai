# Live readiness

- **Project:** YieldMind Engine
- **Track:** Zyfai
- **Latest verification:** `verified`
- **Execution mode:** `offline_prepared`
- **Generated at:** `2026-03-19T03:52:22+00:00`

## Trust boundaries

- **Zyfai** — `rest_json` — Measure yield headroom and budget compute spend.
- **Bankr Gateway** — `rest_json` — Route inference through cost-aware model selection.
- **PayWithLocus** — `rest_json` — Create bounded subaccounts and controlled spend flows.
- **Venice** — `rest_json` — Run private reasoning over sensitive inputs.
- **ERC-8004 Receipts** — `contract_call` — Anchor identity, task receipts, and reputation updates.
- **Uniswap** — `rest_json` — Quote swaps and bounded liquidity moves.
- **Lido** — `contract_call` — Route staking yield through guarded treasury actions.

## Offline-ready partner paths

- **ERC-8004 Receipts** — prepared_contract_call
- **Lido** — prepared_contract_call

## Live-only partner blockers

- **Zyfai**: ZYFAI_API_KEY, ZYFAI_STRATEGY_URL — https://docs.zyf.ai/
- **Bankr Gateway**: BANKR_API_KEY, BANKR_CHAT_COMPLETIONS_URL, BANKR_MODEL — https://bankr.bot/
- **PayWithLocus**: LOCUS_API_KEY, LOCUS_PAYMENT_URL — https://docs.locus.finance/
- **Venice**: VENICE_API_KEY, VENICE_CHAT_COMPLETIONS_URL, VENICE_MODEL — https://docs.venice.ai/
- **Uniswap**: UNISWAP_API_KEY, UNISWAP_QUOTE_URL — https://developers.uniswap.org/

## Highest-sensitivity actions

- `bankr_gateway_compute_route` — Bankr Gateway — Use Bankr Gateway for a bounded action in this repo.
- `venice_private_analysis` — Venice — Use Venice for a bounded action in this repo.

## Exact next steps

- Copy .env.example to .env and fill the required keys.
- Deploy the contract with forge script script/Deploy.s.sol --broadcast for YieldMindController.
- Run python3 scripts/run_agent.py to produce a dry run for zyfai_engine.
- Set LIVE_MODE=true and rerun python3 scripts/run_agent.py with real credentials.
- Run python3 scripts/render_submission.py and attach TxIDs plus repo links.
