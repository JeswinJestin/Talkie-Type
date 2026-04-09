.PHONY: test build ship

test:
	python -m pytest -q

build:
	python -m pip install -r requirements.txt
	python -m pip install -r requirements-dev.txt
	python -m PyInstaller --noconsole --name TalkieType --clean --noconfirm voicetype/__main__.py

ship:
	python scripts/ship.py
