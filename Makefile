.PHONY: data train serve eval test lint setup

setup:
	bash scripts/setup.sh
data:
	python data/collect.py && python data/curate.py && python data/process.py
train:
	python training/scripts/train.py --config training/configs/base.yaml
serve:
	python inference/server/start.py
eval:
	python training/scripts/evaluate.py
test:
	pytest tests/ -v
lint:
	ruff check . && mypy .