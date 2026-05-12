PYTHON   := python
PIP      := pip
OUTPUTS  := outputs

.PHONY: all setup env generate clean-data preview load-sql clean-outputs help

## Default: generate then clean
all: generate clean-data

## Install Python dependencies from requirements.txt
setup:
	$(PIP) install -r requirements.txt

## Create .env from .env.example (skips if .env already exists)
env:
	$(PYTHON) -c "import shutil,os; shutil.copy('.env.example','.env') if not os.path.exists('.env') else print('.env already exists -- skipping')"

## Generate the raw synthetic dataset  ->  outputs/healthcare_dataset_raw.csv
generate:
	$(PYTHON) generate_dataset.py

## Clean the raw dataset  ->  outputs/healthcare_cleaned_full.csv
clean-data:
	$(PYTHON) clean_healthcare_data.py

## Quick 1,000-row preview  ->  outputs/healthcare_cleaned_preview.csv
preview:
	$(PYTHON) clean_healthcare_data.py --preview

## Clean + normalize + bulk-load into SQL Server (run 'make env' first to configure credentials)
load-sql:
	$(PYTHON) clean_healthcare_data.py --load-sql

## Remove all generated output files and recreate the empty outputs/ folder
clean-outputs:
	$(PYTHON) -c "import shutil, os; shutil.rmtree('$(OUTPUTS)', ignore_errors=True); os.makedirs('$(OUTPUTS)')"
	@echo "$(OUTPUTS)/ cleared."

## Show this help message
help:
	@echo "Available targets:"
	@echo "  make setup         Install dependencies (pip install -r requirements.txt)"
	@echo "  make env           Create .env from .env.example (skips if exists)"
	@echo "  make generate      Run generate_dataset.py"
	@echo "  make clean-data    Run clean_healthcare_data.py"
	@echo "  make preview       Run clean_healthcare_data.py --preview (1,000 rows)"
	@echo "  make load-sql      Clean + normalize + load into SQL Server"
	@echo "  make all           generate + clean-data"
	@echo "  make clean-outputs Delete everything in outputs/ and recreate the folder"
	@echo "  make help          Show this message"
