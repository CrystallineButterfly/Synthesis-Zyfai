.PHONY: test plan

test:
	python3 -m unittest discover -s tests

plan:
	python3 scripts/plan_live_demo.py
