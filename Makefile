FUTHARK ?= .tools/bin/futhark
CUDA_ROOT ?= /usr/local/cuda-12.6
CUDA_TARGET ?= $(CUDA_ROOT)/targets/x86_64-linux
CUDA_DRIVER_LIB ?= /usr/lib/wsl/lib
SENS_FIXTURE_SOURCE ?=
FIXTURE_DESTINATION ?= fixtures/imported
CPU_WITNESS ?= host/cpu_witness.py
PARITY_RUNNER ?= host/parity.py
BACKEND_WITNESS ?=

.PHONY: bootstrap probe check check-identity test-identity-cpu test-identity-cuda smoke-opencl smoke-cuda import-fixture witness-cpu witness-parity

bootstrap:
	bash tools/install-futhark.sh

probe:
	bash tools/probe-gpu.sh

check:
	$(FUTHARK) check src/smoke.fut

check-identity:
	$(FUTHARK) check -w futhark/identity_witness.fut

test-identity-cpu:
	$(FUTHARK) test --backend=c futhark/identity_witness.fut

test-identity-cuda:
	test -f "$(CUDA_TARGET)/include/cuda.h"
	CUDA_HOME="$(CUDA_ROOT)" CUDA_PATH="$(CUDA_ROOT)" \
	CPATH="$(CUDA_TARGET)/include${CPATH:+:$CPATH}" \
	LIBRARY_PATH="$(CUDA_DRIVER_LIB):$(CUDA_TARGET)/lib${LIBRARY_PATH:+:$LIBRARY_PATH}" \
	LD_LIBRARY_PATH="$(CUDA_DRIVER_LIB):$(CUDA_TARGET)/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
	$(FUTHARK) test --backend=cuda futhark/identity_witness.fut

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
