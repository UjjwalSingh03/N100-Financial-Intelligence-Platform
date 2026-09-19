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
	python -m src.dashboard.app

api:
	python -m src.api.app

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
