.PHONY: setup analyse test dashboard

setup:
	uv venv .venv
	uv pip install --python .venv/bin/python -r requirements.txt

analyse:
	.venv/bin/python -m src.pipeline

test:
	.venv/bin/python -m pytest -q

dashboard:
	.venv/bin/streamlit run app.py

