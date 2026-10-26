.PHONY: data analysis test all

data:
	python scripts/generate_demo_data.py

analysis:
	python scripts/run_analysis.py

test:
	python -m unittest discover -s tests -v

all: data analysis test
