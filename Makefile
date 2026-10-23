.PHONY: load ratios test report dashboard api clean

load:
	python -m src.etl.database_loader

ratios:
	python -m src.etl.loader --ratios

test:
	pytest -q

report:
	python -m src.etl.report

dashboard:
	streamlit run src/dashboard/app.py

api:
	uvicorn src.api.main:app --port 8000

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
