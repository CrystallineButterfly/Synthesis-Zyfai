
# Security

## Attack surface

- Treasury or identity actions are only modeled through `YieldMindController`.
- Every live action must be preceded by a persisted dry-run artifact.
- Partner endpoints remain env-only and are never hardcoded in source.

## Controls

- Admin-managed allowlists for target contracts and selectors.
- Per-action caps, daily caps, and cooldown windows enforced onchain.
- Pause switch for emergency response.
- Principal floor so only spendable buffer can be used.
- Receipt and proof anchoring for every verified action.

## Remaining blockers

- Real wallets, API keys, and TxIDs must be provided in `.env` before live execution.
- Repo URL, demo URL, and final registration data remain pending until submission time.
