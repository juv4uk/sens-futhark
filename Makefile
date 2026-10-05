FUTHARK ?= .tools/bin/futhark
CUDA_ENV ?= tools/cuda-env.sh
SENS_FIXTURE_SOURCE ?=
FIXTURE_DESTINATION ?= fixtures/imported
CPU_WITNESS ?= host/cpu_witness.py
PARITY_RUNNER ?= host/parity.py
BACKEND_WITNESS ?=
ARGS ?=

.PHONY: bootstrap probe probe-cuda-json check check-identity test-identity-cpu test-identity-cuda check-packed-domain test-packed-domain smoke-opencl smoke-cuda import-fixture witness-cpu witness-parity sens-cli sens-cli-parity verify-sens-pin

bootstrap:
	bash tools/install-futhark.sh

probe:
	bash tools/probe-gpu.sh

probe-cuda-json:
	bash "$(CUDA_ENV)" json

check:
	$(FUTHARK) check src/smoke.fut

check-identity:
	$(FUTHARK) check -w futhark/identity_witness.fut

test-identity-cpu:
	$(FUTHARK) test --backend=c futhark/identity_witness.fut

test-identity-cuda:
	bash "$(CUDA_ENV)" run "$(FUTHARK)" test --backend=cuda futhark/identity_witness.fut

check-packed-domain:
	$(FUTHARK) check -w futhark/packed_domain.fut
	python3 tools/validate-packed-domain-vectors.py

test-packed-domain:
	$(FUTHARK) test --backend=c futhark/packed_domain.fut
	bash "$(CUDA_ENV)" run "$(FUTHARK)" test --backend=cuda futhark/packed_domain.fut

smoke-opencl:
	FUTHARK=$(FUTHARK) bash tools/smoke-opencl.sh

smoke-cuda:
	FUTHARK=$(FUTHARK) bash tools/smoke-cuda.sh

import-fixture:
	@test -n "$(SENS_FIXTURE_SOURCE)" || { echo "SENS_FIXTURE_SOURCE is required; no local fixture fallback exists." >&2; exit 2; }
	python3 host/import_sens_fixture.py --source "$(SENS_FIXTURE_SOURCE)" --destination "$(FIXTURE_DESTINATION)"

witness-cpu:
	@test -f "$(FIXTURE_DESTINATION)/identity_vectors.csv" || { echo "Imported fixture missing; run make import-fixture SENS_FIXTURE_SOURCE=/path/to/sens-bundle first." >&2; exit 2; }
	@python3 -c 'import json; m=json.load(open("$(FIXTURE_DESTINATION)/manifest.json", encoding="utf-8")); print("(provenance (source {}) (commit {}) (contract {}) (sha256 {}))".format(m["source_repository"], m["source_commit"], m["contract_version"], m["payload_sha256"]))'
	python3 "$(CPU_WITNESS)" --fixture "$(FIXTURE_DESTINATION)/identity_vectors.csv"

witness-parity:
	@test -f "$(PARITY_RUNNER)" || { echo "Parity runner missing (#18); backend equality cannot be claimed." >&2; exit 2; }
	@test -n "$(BACKEND_WITNESS)" || { echo "BACKEND_WITNESS is required; absent backend output is not GPU parity." >&2; exit 2; }
	@test -f "$(BACKEND_WITNESS)" || { echo "BACKEND_WITNESS does not exist: $(BACKEND_WITNESS)" >&2; exit 2; }
	@reference=$$(mktemp); trap 'rm -f "$$reference"' EXIT; python3 "$(CPU_WITNESS)" --fixture "$(FIXTURE_DESTINATION)/identity_vectors.csv" > "$$reference" && python3 "$(PARITY_RUNNER)" --reference "$$reference" --backend "$(BACKEND_WITNESS)"

verify-sens-pin:
	bash tools/verify-sens-source-pin.sh

sens-cli:
	bash tools/sens-cli.sh $(ARGS)

sens-cli-parity:
	bash tools/smoke-sens-cli-parity.sh
