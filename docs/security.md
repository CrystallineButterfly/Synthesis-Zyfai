# Security notes for YieldMind Engine

        ## Attack surfaces

        - wallet compromise and bad operator routing
- whitelist bypass or target drift
- excessive spend or missing cooldown checks
- missing dry-run evidence before live execution
- accidental key disclosure through logs or configs

        ## Guardrails

        - AccessControl + pause switch on the policy contract
        - per-action caps and cooldown windows
        - env-only secrets and LIVE_MODE=false by default
        - structured logging for every discover-plan-execute-verify step
        - explicit hold on registration and submission until the human provides JSON
