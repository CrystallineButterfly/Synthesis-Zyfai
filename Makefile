
.PHONY: test test-python test-solidity run plan submission

test: test-python test-solidity

test-python:
	python3 -m unittest discover -s tests

test-solidity:
	forge test

run:
	python3 scripts/run_agent.py

plan:
	python3 scripts/plan_live_demo.py

submission:
	python3 scripts/render_submission.py
