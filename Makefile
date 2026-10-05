# Rhombus AI assessment: every command you need. Run `make help`.
PY := $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
V  := $(PY) data-validation/validate.py

define need_case
	@if [ -z "$(CASE)" ]; then echo "CASE is required, e.g.  make $@ CASE=baseline"; \
	 echo "cases: baseline probe-extra-row S1 S2 S3 S4 S5 M1 M2 M3"; exit 2; fi
endef

.PHONY: help setup datasets test-validator lint check-no-sleeps ci upload latest validate reference \
        determinism predict predict-all validate-all auth har endpoints ui ui-slow ui-e2e api

help:            ## list commands
	@grep -E '^[a-z0-9-]+:.*## ' Makefile | sed -E 's/:.*## /\t/' | expand -t 18

setup:           ## create .venv, install dependencies and the Playwright browser
	python3.11 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt
	.venv/bin/playwright install chromium

datasets:        ## regenerate baseline + drift files (byte-identical, seed 42)
	$(PY) datasets/generate.py

test-validator:  ## unit tests for the validator (offline)
	$(PY) -m pytest data-validation/tests -q

lint:            ## ruff
	$(PY) -m ruff check .

check-no-sleeps: ## fail if any test uses a fixed sleep
	@! grep -RInE "time\.sleep\(|wait_for_timeout\(" ui-tests api-tests --include=*.py \
	  || (echo "fixed sleeps found ^"; exit 1)
	@echo "no fixed sleeps"

ci: lint check-no-sleeps test-validator ## everything CI runs

upload:          ## upload a case to S3            make upload CASE=S1
	$(need_case)
	$(PY) scripts/upload.py --case $(CASE)

latest:          ## list newest outputs in GCS
	$(V) latest

validate:        ## validate newest GCS output     make validate CASE=S1 [OBJECT=name] [FILE=path]
	$(need_case)
	$(V) run --case $(CASE) $(if $(OBJECT),--object $(OBJECT)) $(if $(FILE),--file $(FILE))

reference:       ## freeze the newest passing baseline output as the semantic reference
	$(V) reference

determinism:     ## compare last N outputs         make determinism CASE=baseline [N=3]
	$(need_case)
	$(V) determinism --case $(CASE) --n $(or $(N),3)

predict:         ## literal-rule prediction        make predict CASE=M2
	$(need_case)
	$(V) predict --case $(CASE)

predict-all:     ## predictions for every case
	@for c in baseline probe-extra-row S1 S2 S3 S4 S5 M1 M2 M3; do $(V) predict --case $$c | tail -4; done

validate-all:    ## re-validate every saved output → results/summary.json
	$(V) all

auth:            ## manual login once → .auth/state.json
	$(PY) ui-tests/scripts/save_auth.py

har:             ## record network traffic while you click through Rhombus
	$(PY) api-tests/scripts/record_har.py

endpoints:       ## summarise backend calls from the HAR (no secrets)
	$(PY) api-tests/scripts/har_summary.py api-tests/har/journey.har

ui:              ## UI tests (fast, read-only + scratch CRUD)
	$(PY) -m pytest ui-tests -m "not slow and not e2e"

ui-slow:         ## UI test that runs the pipeline and asserts the GCS object
	$(PY) -m pytest ui-tests -m slow

ui-e2e:          ## AI-build end-to-end in the scratch project (uses credits)
	$(PY) -m pytest ui-tests -m e2e --headed

api:             ## API tests (positive + negative)
	$(PY) -m pytest api-tests
