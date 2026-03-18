from __future__ import annotations

import json

CHECKLIST = {
    'project': 'YieldMind Engine',
    'primary_track': 'Zyfai',
    'steps': [
        'add real wallet addresses to .env',
        'add partner API keys to .env',
        'update agent.json identity fields',
        'run python3 scripts/run_agent.py in dry-run mode',
        'enable LIVE_MODE=true for a controlled live pass',
        'capture TxIDs and paste them into submissions/synthesis.md',
    ],
}


if __name__ == '__main__':
    print(json.dumps(CHECKLIST, indent=2))
