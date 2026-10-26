# Contributing

This project is built for portfolio learning. Changes that improve the analysis are welcome, especially clearer assumptions, better validation, additional checks for score quality, and dashboard accessibility.

Before opening a change:

1. Keep the synthetic-data label in the report and dashboard.
2. Do not add real customer data, personal details, API keys or credentials.
3. Run `python scripts/run_analysis.py` and `python -m unittest discover -s tests -v`.
4. Explain whether a change affects the generated data, the calculations, or how results are shown.
5. Avoid describing correlation or attribution credit as a causal result without a test design to support it.
