checks:
	./scripts/checks.sh

bandit-root-py:
	bandir -r *.py

run:
	python main.py
