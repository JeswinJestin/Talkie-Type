.PHONY: doctor test security build ship

doctor:
	python scripts/doctor.py --strict

test:
	python -m pytest -q

security:
	python -m pip_audit -r requirements.txt
	python -m bandit -q -r voicetype -x voicetype/ui.py,voicetype/tray.py --severity-level medium --confidence-level medium

build:
	python -m pip install -r requirements.txt
	python -m pip install -r requirements-dev.txt
	python -m PyInstaller --noconsole --name TalkieType --clean --noconfirm voicetype/__main__.py

ship:
	python scripts/ship.py
